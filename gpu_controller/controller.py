"""PID 컨트롤러 - GPU 사용률 -> duty-cycle 변환."""

import time as _time
from dataclasses import dataclass


@dataclass
class PIDState:
    """PID 디버깅 정보."""
    error: float = 0.0
    p_term: float = 0.0
    i_term: float = 0.0
    d_term: float = 0.0
    output: float = 0.0


class PIDController:
    """이산 PID 컨트롤러.

    입력: error = target_utilization - current_utilization (0~100 스케일)
    출력: duty_cycle (0.0 ~ 1.0)
    """

    def __init__(self, kp: float, ki: float, kd: float) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time: float | None = None
        self._output = 0.5  # 초기 duty_cycle

        self.state = PIDState()

    def reset(self) -> None:
        """컨트롤러 상태 초기화."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time = None
        self._output = 0.5

    def update(self, current_utilization: float, target_utilization: float, dt: float | None = None) -> float:
        """현재 사용률을 받아 새 duty_cycle 반환.

        Positional PID: output = kp*error + ki*integral + kd*derivative
        오차를 0~100 스케일에서 계산하고 결과를 0.0~1.0으로 클램핑.

        dt를 명시하면 시간 계산을 건너뛰고 해당 값 사용 (테스트용).
        """
        error = target_utilization - current_utilization

        if dt is None:
            now = _time.monotonic()
            if self._last_time is None:
                dt = 1.0
            else:
                dt = now - self._last_time
                if dt <= 0:
                    dt = 1.0
            self._last_time = now
        else:
            if dt <= 0:
                dt = 1.0

        # 적분 (anti-windup: 클램핑)
        self._integral += error * dt
        self._integral = max(-100.0, min(100.0, self._integral))

        # 미분
        derivative = (error - self._prev_error) / dt

        # PID 항 계산
        p_term = self.kp * error
        i_term = self.ki * self._integral
        d_term = self.kd * derivative

        # 출력: 기준점(0.5) + PID 보정 -> 0.0~1.0 클램핑
        raw = 0.5 + p_term + i_term + d_term
        self._output = max(0.0, min(1.0, raw))

        # 상태 업데이트
        self._prev_error = error

        self.state = PIDState(
            error=error,
            p_term=p_term,
            i_term=i_term,
            d_term=d_term,
            output=self._output,
        )

        return self._output
