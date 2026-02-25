# GPU Utilization Controller

GPU 사용률을 특정 시간대에 목표 퍼센트로 유지하는 프로그램입니다.

## 요구 사항

- Linux + NVIDIA GPU (H100 권장)
- CUDA 12.1+
- Python 3.10+

## 설치

```bash
chmod +x setup.sh
./setup.sh
```

또는 수동 설치:

```bash
python3 -m venv venv
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu126
pip install nvidia-ml-py PyYAML
```

## 설정

`config.example.yaml`을 `config.yaml`으로 복사 후 수정:

```bash
cp config.example.yaml config.yaml
```

주요 설정:

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `schedule.start_time` | 시작 시간 (HH:MM) | `18:00` |
| `schedule.end_time` | 종료 시간 (HH:MM) | `23:59` |
| `target_utilization` | 목표 GPU 사용률 (1-100%) | `70` |
| `gpus` | `"all"` 또는 인덱스 리스트 `[0, 1]` | `"all"` |

자정 넘김도 지원합니다 (예: `22:00` ~ `06:00`).

## 실행

```bash
source venv/bin/activate
python -m gpu_controller --config config.yaml
```

### CLI 옵션

| 옵션 | 설명 |
|------|------|
| `--config`, `-c` | 설정 파일 경로 (기본: `config.yaml`) |
| `--dry-run` | 설정만 로드하고 종료 |
| `--once` | 제어 루프 1회만 실행 후 종료 |
| `--log-level` | 로그 레벨 오버라이드 (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### 종료

`Ctrl+C` 또는 `SIGTERM`으로 안전하게 종료됩니다.

## 작동 원리

1. **Duty-Cycle 변조**: 고정 주기(100ms) 내에서 compute/sleep 비율 조절
2. **PID 컨트롤러**: 목표 사용률과 현재 사용률의 오차를 기반으로 duty-cycle 조절
3. **스케줄링**: 설정된 시간대에만 활성화

## 테스트

```bash
# 단위 테스트 (GPU 불필요)
pytest tests/test_config.py tests/test_controller.py tests/test_scheduler.py -v

# 통합 테스트 (GPU 필요)
pytest tests/test_monitor.py tests/test_workload.py -v
```

## 가이드

상세한 실행 가이드는 [GUIDE.md](GUIDE.md)를 참조하세요.

## 라이선스

[LICENSE](LICENSE) 참조.
