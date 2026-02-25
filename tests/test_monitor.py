"""monitor.py 단위 테스트 — pynvml 모킹."""

import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from gpu_controller.monitor import GPUMonitor, GPUStatus


@pytest.fixture
def mock_nvml():
    """pynvml 함수들을 모킹."""
    with patch("gpu_controller.monitor.pynvml") as mock:
        mock.nvmlInit = MagicMock()
        mock.nvmlShutdown = MagicMock()
        mock.nvmlDeviceGetCount = MagicMock(return_value=2)
        mock.nvmlDeviceGetHandleByIndex = MagicMock(return_value="handle")
        mock.nvmlDeviceGetName = MagicMock(return_value="NVIDIA H100")
        mock.nvmlDeviceGetUtilizationRates = MagicMock(
            return_value=SimpleNamespace(gpu=65, memory=40)
        )
        mock.NVML_TEMPERATURE_GPU = 0
        mock.nvmlDeviceGetTemperature = MagicMock(return_value=55)
        mock.nvmlDeviceGetPowerUsage = MagicMock(return_value=300000)  # 300W in mW
        mock.nvmlDeviceGetMemoryInfo = MagicMock(
            return_value=SimpleNamespace(used=40 * 1024**3, total=80 * 1024**3)
        )
        mock.NVMLError = Exception
        yield mock


class TestGPUMonitor:
    def test_init(self, mock_nvml):
        mon = GPUMonitor()
        mock_nvml.nvmlInit.assert_called_once()
        assert mon.get_device_count() == 2

    def test_get_status(self, mock_nvml):
        mon = GPUMonitor()
        status = mon.get_status(0)
        assert isinstance(status, GPUStatus)
        assert status.index == 0
        assert status.name == "NVIDIA H100"
        assert status.gpu_utilization == 65.0
        assert status.memory_utilization == 40.0
        assert status.temperature == 55
        assert status.power_draw == 300.0
        assert status.memory_used == 40 * 1024**3
        assert status.memory_total == 80 * 1024**3

    def test_get_status_bytes_name(self, mock_nvml):
        """GPU 이름이 bytes로 반환되는 경우."""
        mock_nvml.nvmlDeviceGetName.return_value = b"NVIDIA H100"
        mon = GPUMonitor()
        status = mon.get_status(0)
        assert status.name == "NVIDIA H100"

    def test_get_all_status(self, mock_nvml):
        mon = GPUMonitor()
        statuses = mon.get_all_status()
        assert len(statuses) == 2
        assert statuses[0].index == 0
        assert statuses[1].index == 1

    def test_get_all_status_partial_failure(self, mock_nvml):
        """일부 GPU 실패 시 나머지는 정상 반환."""
        call_count = 0

        def side_effect(idx):
            nonlocal call_count
            call_count += 1
            if idx == 1:
                raise Exception("GPU 1 오류")
            return "handle"

        mock_nvml.nvmlDeviceGetHandleByIndex = MagicMock(side_effect=side_effect)
        mon = GPUMonitor()
        statuses = mon.get_all_status()
        assert len(statuses) == 1
        assert statuses[0].index == 0

    def test_shutdown(self, mock_nvml):
        mon = GPUMonitor()
        mon.shutdown()
        mock_nvml.nvmlShutdown.assert_called_once()
