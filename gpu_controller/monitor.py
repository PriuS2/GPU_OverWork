"""pynvml 기반 GPU 모니터링."""

import logging
from dataclasses import dataclass

import pynvml

logger = logging.getLogger(__name__)


@dataclass
class GPUStatus:
    """단일 GPU 상태 정보."""
    index: int
    name: str
    gpu_utilization: float   # 0-100
    memory_utilization: float  # 0-100
    temperature: int          # °C
    power_draw: float         # W
    memory_used: int          # bytes
    memory_total: int         # bytes


class GPUMonitor:
    """pynvml로 GPU 상태를 조회."""

    def __init__(self) -> None:
        pynvml.nvmlInit()
        self._device_count = pynvml.nvmlDeviceGetCount()
        logger.info("NVML 초기화 완료 - GPU %d개 감지", self._device_count)

    def get_device_count(self) -> int:
        return self._device_count

    def get_status(self, gpu_index: int) -> GPUStatus:
        """지정 GPU의 현재 상태를 반환."""
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")

        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW -> W
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

        return GPUStatus(
            index=gpu_index,
            name=name,
            gpu_utilization=float(util.gpu),
            memory_utilization=float(util.memory),
            temperature=temp,
            power_draw=power,
            memory_used=mem.used,
            memory_total=mem.total,
        )

    def get_all_status(self) -> list[GPUStatus]:
        """모든 GPU의 상태를 반환."""
        results = []
        for i in range(self._device_count):
            try:
                results.append(self.get_status(i))
            except pynvml.NVMLError as e:
                logger.error("GPU %d 상태 조회 실패: %s", i, e)
        return results

    def shutdown(self) -> None:
        """NVML 종료."""
        try:
            pynvml.nvmlShutdown()
            logger.info("NVML 종료 완료")
        except pynvml.NVMLError:
            pass
