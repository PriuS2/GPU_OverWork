"""workload.py 단위 테스트 — torch/CUDA 모킹."""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock

from gpu_controller.workload import GPUWorkload


class TestGPUWorkloadUnit:
    def test_duty_cycle_property(self):
        wl = GPUWorkload(gpu_index=0)
        assert wl.duty_cycle == 0.5

        wl.duty_cycle = 0.8
        assert wl.duty_cycle == 0.8

    def test_duty_cycle_clamped(self):
        wl = GPUWorkload(gpu_index=0)
        wl.duty_cycle = 1.5
        assert wl.duty_cycle == 1.0
        wl.duty_cycle = -0.5
        assert wl.duty_cycle == 0.0

    def test_not_running_initially(self):
        wl = GPUWorkload(gpu_index=0)
        assert wl.running is False

    def test_stop_when_not_running(self):
        """실행 중이 아닐 때 stop 호출해도 에러 없음."""
        wl = GPUWorkload(gpu_index=0)
        wl.stop()  # 예외 없어야 함

    def test_start_already_running(self):
        """이미 실행 중이면 start가 무시됨."""
        wl = GPUWorkload(gpu_index=0)
        wl._running = True
        wl.start()  # 새 스레드 생성 안 함
        assert wl._thread is None

    @patch("gpu_controller.workload.torch")
    def test_start_stop_lifecycle(self, mock_torch):
        """start/stop 라이프사이클 테스트 (모킹)."""
        mock_device = MagicMock()
        mock_torch.device.return_value = mock_device
        mock_torch.randn.return_value = MagicMock()
        mock_torch.mm.return_value = MagicMock()
        mock_torch.cuda.synchronize = MagicMock()
        mock_torch.cuda.empty_cache = MagicMock()
        mock_torch.cuda.OutOfMemoryError = MemoryError

        wl = GPUWorkload(gpu_index=0, matrix_size=64, cycle_period=0.01)
        wl.start()
        assert wl.running is True

        time.sleep(0.05)  # 약간의 실행 시간

        wl.stop()
        assert wl.running is False

    def test_matrix_size_attribute(self):
        wl = GPUWorkload(gpu_index=0, matrix_size=2048)
        assert wl.matrix_size == 2048

    def test_cycle_period_attribute(self):
        wl = GPUWorkload(gpu_index=0, cycle_period=0.2)
        assert wl.cycle_period == 0.2
