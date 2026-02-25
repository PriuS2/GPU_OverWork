"""YAML 설정 파일 로드 및 검증."""

import copy
import re
from pathlib import Path

import yaml

DEFAULTS = {
    "schedule": {
        "start_time": "09:00",
        "end_time": "18:00",
    },
    "target_utilization": 70,
    "gpus": "all",
    "control": {
        "interval_seconds": 2.0,
        "pid_kp": 0.005,
        "pid_ki": 0.003,
        "pid_kd": 0.001,
        "matrix_size": 4096,
        "cycle_period": 0.02,
    },
    "log_file": "gpu_controller.log",
    "log_level": "INFO",
}

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _deep_merge(base: dict, override: dict) -> dict:
    """base 딕셔너리에 override를 재귀적으로 병합."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _validate(cfg: dict) -> None:
    """설정값 검증. 유효하지 않으면 ValueError 발생."""
    schedule = cfg.get("schedule", {})
    for field in ("start_time", "end_time"):
        val = schedule.get(field, "")
        if not _TIME_RE.match(str(val)):
            raise ValueError(f"schedule.{field} 형식이 잘못됨: '{val}' (HH:MM 필요)")

    util = cfg.get("target_utilization")
    if not isinstance(util, (int, float)) or not (1 <= util <= 100):
        raise ValueError(f"target_utilization은 1~100 사이여야 함: {util}")

    gpus = cfg.get("gpus")
    if gpus != "all":
        if not isinstance(gpus, list) or not all(isinstance(i, int) and i >= 0 for i in gpus):
            raise ValueError(f"gpus는 'all' 또는 0 이상의 정수 리스트여야 함: {gpus}")

    ctrl = cfg.get("control", {})
    if ctrl.get("interval_seconds", 0) <= 0:
        raise ValueError("control.interval_seconds는 0보다 커야 함")
    for pid_key in ("pid_kp", "pid_ki", "pid_kd"):
        if ctrl.get(pid_key, 0) < 0:
            raise ValueError(f"control.{pid_key}는 0 이상이어야 함")
    if ctrl.get("matrix_size", 0) < 64:
        raise ValueError("control.matrix_size는 64 이상이어야 함")
    if ctrl.get("cycle_period", 0) <= 0:
        raise ValueError("control.cycle_period는 0보다 커야 함")


def load_config(path: str | Path) -> dict:
    """YAML 설정 파일을 로드하고 기본값과 병합 후 검증."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없음: {path}")

    with open(path, "r", encoding="utf-8") as f:
        user_cfg = yaml.safe_load(f) or {}

    cfg = _deep_merge(DEFAULTS, user_cfg)
    _validate(cfg)
    return cfg
