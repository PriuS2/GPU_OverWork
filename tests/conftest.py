"""공유 pytest fixture."""

import pytest
import tempfile
import os

import yaml


@pytest.fixture
def valid_config_dict():
    """유효한 설정 딕셔너리."""
    return {
        "schedule": {"start_time": "18:00", "end_time": "23:59"},
        "target_utilization": 70,
        "gpus": "all",
        "control": {
            "interval_seconds": 1.0,
            "pid_kp": 0.01,
            "pid_ki": 0.005,
            "pid_kd": 0.002,
            "matrix_size": 4096,
            "cycle_period": 0.1,
        },
        "log_file": "gpu_controller.log",
        "log_level": "INFO",
    }


@pytest.fixture
def config_file(valid_config_dict, tmp_path):
    """임시 YAML 설정 파일 경로."""
    path = tmp_path / "config.yaml"
    with open(path, "w") as f:
        yaml.dump(valid_config_dict, f)
    return str(path)
