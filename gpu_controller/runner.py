"""메인 오케스트레이션 루프 - GPU별 PID + 워크로드 관리."""

import logging
import threading

from .controller import PIDController
from .monitor import GPUMonitor
from .scheduler import Scheduler
from .workload import GPUWorkload

logger = logging.getLogger(__name__)


class Runner:
    """GPU 사용률 제어 메인 루프.

    스케줄러가 활성이면 워크로드를 시작하고 PID로 duty-cycle을 조절합니다.
    비활성이면 워크로드를 중지합니다.
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self.shutdown_event = threading.Event()

        schedule = config["schedule"]
        self.scheduler = Scheduler(schedule["start_time"], schedule["end_time"])

        self.target = float(config["target_utilization"])
        ctrl = config["control"]
        self.interval = ctrl["interval_seconds"]
        self.matrix_size = ctrl["matrix_size"]
        self.cycle_period = ctrl["cycle_period"]

        self._monitor: GPUMonitor | None = None
        self._gpu_indices: list[int] = []
        self._controllers: dict[int, PIDController] = {}
        self._workloads: dict[int, GPUWorkload] = {}
        self._ema: dict[int, float | None] = {}  # GPU별 EMA 필터 값
        self._ema_alpha = 0.3  # EMA 계수 (0에 가까울수록 평활)
        self._active = False

    def _init_gpus(self) -> None:
        """GPU 모니터 초기화 + 대상 GPU 인덱스 결정."""
        self._monitor = GPUMonitor()
        device_count = self._monitor.get_device_count()

        gpus = self.config["gpus"]
        if gpus == "all":
            self._gpu_indices = list(range(device_count))
        else:
            for idx in gpus:
                if idx >= device_count:
                    raise ValueError(f"GPU 인덱스 {idx}이 범위 초과 (총 {device_count}개)")
            self._gpu_indices = list(gpus)

        ctrl = self.config["control"]
        for idx in self._gpu_indices:
            self._controllers[idx] = PIDController(
                kp=ctrl["pid_kp"],
                ki=ctrl["pid_ki"],
                kd=ctrl["pid_kd"],
            )
            self._workloads[idx] = GPUWorkload(
                gpu_index=idx,
                matrix_size=self.matrix_size,
                cycle_period=self.cycle_period,
            )

        self._ema = {idx: None for idx in self._gpu_indices}
        logger.info("대상 GPU: %s (목표 사용률: %.0f%%)", self._gpu_indices, self.target)

    def _start_workloads(self) -> None:
        """모든 워크로드 시작."""
        for idx in self._gpu_indices:
            self._workloads[idx].start()
        self._active = True
        logger.info("활성 구간 진입 - 워크로드 시작")

    def _stop_workloads(self) -> None:
        """모든 워크로드 중지 + PID 리셋."""
        for idx in self._gpu_indices:
            self._workloads[idx].stop()
            self._controllers[idx].reset()
        self._active = False
        logger.info("비활성 구간 - 워크로드 중지")

    def _control_step(self) -> None:
        """1회 제어 루프: 모니터링 -> EMA 필터 -> PID 업데이트 -> duty_cycle 설정."""
        for idx in self._gpu_indices:
            try:
                status = self._monitor.get_status(idx)
                raw = status.gpu_utilization

                # EMA 필터로 NVML 측정 노이즈 평활
                if self._ema[idx] is None:
                    self._ema[idx] = raw
                else:
                    self._ema[idx] = self._ema_alpha * raw + (1 - self._ema_alpha) * self._ema[idx]
                smoothed = self._ema[idx]

                pid = self._controllers[idx]
                new_dc = pid.update(smoothed, self.target)
                self._workloads[idx].duty_cycle = new_dc

                logger.debug(
                    "GPU %d: raw=%.0f%% ema=%.1f%% target=%.1f%% dc=%.3f err=%.1f",
                    idx, raw, smoothed, self.target, new_dc, pid.state.error,
                )
            except Exception:
                logger.exception("GPU %d 제어 단계 오류", idx)

    def run(self, once: bool = False) -> None:
        """메인 루프 실행. once=True면 1회만 실행."""
        self._init_gpus()

        try:
            while not self.shutdown_event.is_set():
                if self.scheduler.is_active():
                    if not self._active:
                        self._start_workloads()
                    self._control_step()
                else:
                    if self._active:
                        self._stop_workloads()

                if once:
                    break

                self.shutdown_event.wait(timeout=self.interval)
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """종료 시 정리: 워크로드 중지 + NVML 종료."""
        if self._active:
            self._stop_workloads()
        if self._monitor:
            self._monitor.shutdown()
        logger.info("Runner 종료 완료")

    def shutdown(self) -> None:
        """외부에서 호출: graceful shutdown 트리거."""
        logger.info("Shutdown 요청 수신")
        self.shutdown_event.set()
