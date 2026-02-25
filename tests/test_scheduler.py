"""scheduler.py 단위 테스트."""

import pytest
from datetime import datetime

from gpu_controller.scheduler import Scheduler


class TestScheduler:
    def test_within_range(self):
        s = Scheduler("09:00", "18:00")
        assert s.is_active(datetime(2024, 1, 1, 12, 0)) is True

    def test_before_range(self):
        s = Scheduler("09:00", "18:00")
        assert s.is_active(datetime(2024, 1, 1, 8, 59)) is False

    def test_at_start(self):
        s = Scheduler("09:00", "18:00")
        assert s.is_active(datetime(2024, 1, 1, 9, 0)) is True

    def test_at_end(self):
        """end_time은 미포함 (exclusive)."""
        s = Scheduler("09:00", "18:00")
        assert s.is_active(datetime(2024, 1, 1, 18, 0)) is False

    def test_after_range(self):
        s = Scheduler("09:00", "18:00")
        assert s.is_active(datetime(2024, 1, 1, 23, 0)) is False

    def test_midnight_crossing_before_midnight(self):
        """자정 넘김: 22:00~06:00, 23:00은 활성."""
        s = Scheduler("22:00", "06:00")
        assert s.is_active(datetime(2024, 1, 1, 23, 0)) is True

    def test_midnight_crossing_after_midnight(self):
        """자정 넘김: 22:00~06:00, 03:00은 활성."""
        s = Scheduler("22:00", "06:00")
        assert s.is_active(datetime(2024, 1, 2, 3, 0)) is True

    def test_midnight_crossing_outside(self):
        """자정 넘김: 22:00~06:00, 12:00은 비활성."""
        s = Scheduler("22:00", "06:00")
        assert s.is_active(datetime(2024, 1, 1, 12, 0)) is False

    def test_midnight_crossing_at_end(self):
        """자정 넘김: end_time은 미포함."""
        s = Scheduler("22:00", "06:00")
        assert s.is_active(datetime(2024, 1, 2, 6, 0)) is False

    def test_same_start_end(self):
        """start == end이면 항상 비활성."""
        s = Scheduler("12:00", "12:00")
        assert s.is_active(datetime(2024, 1, 1, 12, 0)) is False
        assert s.is_active(datetime(2024, 1, 1, 11, 59)) is False

    def test_full_day(self):
        """00:00~23:59면 거의 하루 종일 활성."""
        s = Scheduler("00:00", "23:59")
        assert s.is_active(datetime(2024, 1, 1, 0, 0)) is True
        assert s.is_active(datetime(2024, 1, 1, 12, 0)) is True
        assert s.is_active(datetime(2024, 1, 1, 23, 58)) is True

    def test_default_now(self):
        """인자 없이 호출하면 현재 시각 사용 (예외 없이 동작)."""
        s = Scheduler("00:00", "23:59")
        result = s.is_active()
        assert isinstance(result, bool)
