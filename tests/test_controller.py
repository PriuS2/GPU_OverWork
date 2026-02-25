"""controller.py 단위 테스트."""

import pytest

from gpu_controller.controller import PIDController, PIDState


class TestPIDController:
    def test_initial_output(self):
        pid = PIDController(kp=0.01, ki=0.005, kd=0.002)
        # 첫 호출 — 오차가 양수(target > current)이면 duty_cycle 증가
        dc = pid.update(current_utilization=50, target_utilization=70)
        assert 0.0 <= dc <= 1.0

    def test_output_increases_when_below_target(self):
        pid = PIDController(kp=0.01, ki=0.005, kd=0.002)
        dc1 = pid.update(30, 70)
        dc2 = pid.update(30, 70)
        # 계속 목표 미달이면 duty_cycle 증가
        assert dc2 >= dc1

    def test_output_decreases_when_above_target(self):
        pid = PIDController(kp=0.01, ki=0.005, kd=0.002)
        # 먼저 높은 duty_cycle 확보
        for _ in range(20):
            pid.update(30, 70)
        dc_high = pid.update(30, 70)
        # 이제 사용률이 목표 초과
        dc_lower = pid.update(90, 70)
        assert dc_lower < dc_high

    def test_output_clamped_to_range(self):
        pid = PIDController(kp=1.0, ki=1.0, kd=0.0)
        # 극단적 게인으로 클램핑 확인
        dc = pid.update(0, 100)
        assert dc <= 1.0
        dc = pid.update(100, 0)
        assert dc >= 0.0

    def test_reset(self):
        pid = PIDController(kp=0.01, ki=0.005, kd=0.002)
        pid.update(30, 70)
        pid.update(30, 70)
        pid.reset()
        assert pid._integral == 0.0
        assert pid._prev_error == 0.0
        assert pid._output == 0.5

    def test_state_populated(self):
        pid = PIDController(kp=0.01, ki=0.005, kd=0.002)
        pid.update(50, 70)
        s = pid.state
        assert isinstance(s, PIDState)
        assert s.error == 20.0
        assert s.output >= 0.0

    def test_converges_to_target(self):
        """시뮬레이션: PID가 목표에 수렴하는지 확인 (고정 dt=1.0)."""
        pid = PIDController(kp=0.005, ki=0.003, kd=0.001)
        simulated_util = 0.0

        for _ in range(500):
            dc = pid.update(simulated_util, 70, dt=1.0)
            # 간단한 시뮬레이션: dc에 비례해 사용률 변화
            simulated_util = dc * 100.0

        assert abs(simulated_util - 70) < 5, f"수렴 실패: {simulated_util}"

    def test_zero_gains(self):
        """게인이 0이면 초기 duty_cycle(0.5) 유지."""
        pid = PIDController(kp=0.0, ki=0.0, kd=0.0)
        dc = pid.update(50, 70)
        assert dc == 0.5
