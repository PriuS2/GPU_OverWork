"""config.py 단위 테스트."""

import pytest
import yaml

from gpu_controller.config import load_config, _deep_merge, _validate


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 3}}
        result = _deep_merge(base, override)
        assert result == {"x": {"a": 1, "b": 3}}

    def test_does_not_mutate_base(self):
        base = {"x": {"a": 1}}
        override = {"x": {"b": 2}}
        _deep_merge(base, override)
        assert base == {"x": {"a": 1}}


class TestValidate:
    def test_valid_config(self, valid_config_dict):
        _validate(valid_config_dict)  # 예외 없어야 함

    def test_invalid_time_format(self, valid_config_dict):
        valid_config_dict["schedule"]["start_time"] = "25:00"
        with pytest.raises(ValueError, match="start_time"):
            _validate(valid_config_dict)

    def test_invalid_time_format_no_colon(self, valid_config_dict):
        valid_config_dict["schedule"]["end_time"] = "1800"
        with pytest.raises(ValueError, match="end_time"):
            _validate(valid_config_dict)

    def test_utilization_too_low(self, valid_config_dict):
        valid_config_dict["target_utilization"] = 0
        with pytest.raises(ValueError, match="target_utilization"):
            _validate(valid_config_dict)

    def test_utilization_too_high(self, valid_config_dict):
        valid_config_dict["target_utilization"] = 101
        with pytest.raises(ValueError, match="target_utilization"):
            _validate(valid_config_dict)

    def test_invalid_gpus(self, valid_config_dict):
        valid_config_dict["gpus"] = "some_string"
        with pytest.raises(ValueError, match="gpus"):
            _validate(valid_config_dict)

    def test_gpus_negative_index(self, valid_config_dict):
        valid_config_dict["gpus"] = [-1]
        with pytest.raises(ValueError, match="gpus"):
            _validate(valid_config_dict)

    def test_gpus_list_valid(self, valid_config_dict):
        valid_config_dict["gpus"] = [0, 1]
        _validate(valid_config_dict)  # 예외 없어야 함

    def test_negative_pid_gain(self, valid_config_dict):
        valid_config_dict["control"]["pid_kp"] = -0.1
        with pytest.raises(ValueError, match="pid_kp"):
            _validate(valid_config_dict)

    def test_small_matrix_size(self, valid_config_dict):
        valid_config_dict["control"]["matrix_size"] = 32
        with pytest.raises(ValueError, match="matrix_size"):
            _validate(valid_config_dict)

    def test_zero_interval(self, valid_config_dict):
        valid_config_dict["control"]["interval_seconds"] = 0
        with pytest.raises(ValueError, match="interval_seconds"):
            _validate(valid_config_dict)


class TestLoadConfig:
    def test_load_valid(self, config_file):
        cfg = load_config(config_file)
        assert cfg["target_utilization"] == 70
        assert cfg["schedule"]["start_time"] == "18:00"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.yaml")

    def test_defaults_applied(self, tmp_path):
        """최소한의 설정만 있을 때 기본값이 적용되는지."""
        path = tmp_path / "minimal.yaml"
        with open(path, "w") as f:
            yaml.dump({"target_utilization": 50}, f)
        cfg = load_config(str(path))
        assert cfg["schedule"]["start_time"] == "09:00"
        assert cfg["control"]["pid_kp"] == 0.005
        assert cfg["target_utilization"] == 50

    def test_empty_file(self, tmp_path):
        """빈 파일은 기본값으로 로드."""
        path = tmp_path / "empty.yaml"
        path.write_text("")
        cfg = load_config(str(path))
        assert cfg["target_utilization"] == 70
