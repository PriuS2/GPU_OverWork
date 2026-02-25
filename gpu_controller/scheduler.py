"""시간 기반 스케줄링 - 활성 구간 판단."""

from datetime import datetime, time


class Scheduler:
    """start_time~end_time 구간 활성 여부를 판단. 자정 넘김도 지원."""

    def __init__(self, start_time: str, end_time: str) -> None:
        self.start = self._parse(start_time)
        self.end = self._parse(end_time)

    @staticmethod
    def _parse(t: str) -> time:
        h, m = t.split(":")
        return time(int(h), int(m))

    def is_active(self, now: datetime | None = None) -> bool:
        """현재 시각(또는 now)이 활성 구간이면 True."""
        if now is None:
            now = datetime.now()
        cur = now.time()

        if self.start <= self.end:
            # 같은 날 구간: start <= cur < end
            return self.start <= cur < self.end
        else:
            # 자정 넘김: start <= cur OR cur < end
            return cur >= self.start or cur < self.end
