"""PyTorch 기반 GPU 부하 생성 - duty-cycle 변조."""

import logging
import threading
import time

import torch

logger = logging.getLogger(__name__)


class GPUWorkload:
    """GPU별 독립 daemon 스레드로 duty-cycle 기반 부하 생성.

    duty_cycle (0.0~1.0)에 따라 cycle_period 내에서
    compute/sleep 비율을 조절합니다.
    """

    def __init__(self, gpu_index: int, matrix_size: int = 4096, cycle_period: float = 0.1) -> None:
        self.gpu_index = gpu_index
        self.matrix_size = matrix_size
        self.cycle_period = cycle_period

        self._duty_cycle = 0.5
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def duty_cycle(self) -> float:
        with self._lock:
            return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value: float) -> None:
        with self._lock:
            self._duty_cycle = max(0.0, min(1.0, value))

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        """워크로드 스레드 시작."""
        if self._running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"gpu-workload-{self.gpu_index}",
            daemon=True,
        )
        self._thread.start()
        self._running = True
        logger.info("GPU %d 워크로드 시작 (matrix=%d)", self.gpu_index, self.matrix_size)

    def stop(self) -> None:
        """워크로드 스레드 중지 + GPU 메모리 해제 대기."""
        if not self._running:
            return
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._running = False
        logger.info("GPU %d 워크로드 중지", self.gpu_index)

    def _run(self) -> None:
        """워크로드 메인 루프."""
        device = torch.device(f"cuda:{self.gpu_index}")
        mat_a, mat_b = self._allocate_matrices(device)
        if mat_a is None:
            return

        try:
            while not self._stop_event.is_set():
                dc = self.duty_cycle
                compute_time = self.cycle_period * dc
                sleep_time = self.cycle_period * (1.0 - dc)

                # 작업 단계
                if compute_time > 0:
                    start = time.monotonic()
                    while time.monotonic() - start < compute_time:
                        if self._stop_event.is_set():
                            return
                        try:
                            torch.mm(mat_a, mat_b)
                            torch.cuda.synchronize(device)
                        except torch.cuda.OutOfMemoryError:
                            mat_a, mat_b = self._handle_oom(device, mat_a, mat_b)
                            if mat_a is None:
                                return

                # 휴식 단계
                if sleep_time > 0.001:
                    self._stop_event.wait(timeout=sleep_time)
        finally:
            del mat_a, mat_b
            torch.cuda.empty_cache()
            logger.debug("GPU %d 메모리 해제 완료", self.gpu_index)

    def _allocate_matrices(self, device: torch.device) -> tuple:
        """행렬 할당. OOM 시 크기를 줄여 재시도."""
        size = self.matrix_size
        while size >= 64:
            try:
                a = torch.randn(size, size, device=device, dtype=torch.float32)
                b = torch.randn(size, size, device=device, dtype=torch.float32)
                logger.debug("GPU %d 행렬 할당 성공: %dx%d", self.gpu_index, size, size)
                self.matrix_size = size
                return a, b
            except torch.cuda.OutOfMemoryError:
                logger.warning("GPU %d OOM - 행렬 크기 %d->%d로 축소", self.gpu_index, size, size // 2)
                torch.cuda.empty_cache()
                size //= 2
        logger.error("GPU %d 행렬 할당 실패: 최소 크기에서도 OOM", self.gpu_index)
        return None, None

    def _handle_oom(self, device: torch.device, old_a, old_b) -> tuple:
        """런타임 OOM 처리: 기존 행렬 해제 + 축소 재할당."""
        del old_a, old_b
        torch.cuda.empty_cache()
        new_size = max(64, self.matrix_size // 2)
        logger.warning("GPU %d 런타임 OOM - 행렬 크기 %d->%d로 축소", self.gpu_index, self.matrix_size, new_size)
        self.matrix_size = new_size
        return self._allocate_matrices(device)
