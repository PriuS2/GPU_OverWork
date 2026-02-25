# GPU Utilization Controller - 실행 가이드

## 목차

1. [사전 요구 사항](#1-사전-요구-사항)
2. [설치](#2-설치)
3. [설정 파일 작성](#3-설정-파일-작성)
4. [실행](#4-실행)
5. [모니터링](#5-모니터링)
6. [종료](#6-종료)
7. [운영 시나리오별 설정 예시](#7-운영-시나리오별-설정-예시)
8. [PID 튜닝 가이드](#8-pid-튜닝-가이드)
9. [트러블슈팅](#9-트러블슈팅)
10. [테스트](#10-테스트)

---

## 1. 사전 요구 사항

| 항목 | 최소 버전 | 확인 명령 |
|------|-----------|-----------|
| OS | Linux (Ubuntu 20.04+) | `uname -a` |
| NVIDIA Driver | 525+ | `nvidia-smi` |
| CUDA | 12.1+ | `nvcc --version` |
| Python | 3.10+ | `python3 --version` |
| GPU | NVIDIA (H100 권장) | `nvidia-smi -L` |

### 사전 확인

```bash
# GPU 인식 확인
nvidia-smi

# CUDA 확인
nvidia-smi | grep "CUDA Version"

# Python 버전 확인
python3 --version
```

---

## 2. 설치

### 방법 A: 자동 설치 (권장)

```bash
cd GPU_OverWork
chmod +x setup.sh
./setup.sh
```

이 스크립트는 다음을 수행합니다:
- `venv` Python 가상환경 생성
- PyTorch (CUDA 12.6) 설치
- `nvidia-ml-py`, `PyYAML` 설치
- `pytest` 설치
- `config.example.yaml` → `config.yaml` 복사 (없을 경우)

### 방법 B: 수동 설치

```bash
cd GPU_OverWork

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu126
pip install nvidia-ml-py PyYAML

# 설정 파일 준비
cp config.example.yaml config.yaml
```

> **참고**: CUDA 버전에 맞는 PyTorch를 설치해야 합니다.
> CUDA 12.1 환경이라면 `cu126`을 `cu121`로 변경하세요.

---

## 3. 설정 파일 작성

`config.yaml`을 편집합니다:

```yaml
schedule:
  start_time: "18:00"       # 시작 시간 (HH:MM, 24시간제)
  end_time: "23:59"         # 종료 시간 (HH:MM, 24시간제)

target_utilization: 70       # 목표 GPU 사용률 (1-100%)

gpus: "all"                  # "all" 또는 GPU 인덱스 목록 [0, 1]

control:
  interval_seconds: 1.0      # 제어 루프 주기 (초)
  pid_kp: 0.01               # PID 비례 게인
  pid_ki: 0.005              # PID 적분 게인
  pid_kd: 0.002              # PID 미분 게인
  matrix_size: 4096          # NxN 행렬 크기
  cycle_period: 0.1          # duty-cycle 주기 (초)

log_file: "gpu_controller.log"
log_level: "INFO"            # DEBUG, INFO, WARNING, ERROR
```

### 설정 항목 상세

#### schedule

| 항목 | 설명 | 형식 | 예시 |
|------|------|------|------|
| `start_time` | 워크로드 시작 시각 | `HH:MM` (24시간) | `"18:00"` |
| `end_time` | 워크로드 종료 시각 | `HH:MM` (24시간) | `"23:59"` |

- **자정 넘김 지원**: `start_time`이 `end_time`보다 클 경우 자정을 넘겨 동작합니다.
  - 예: `"22:00"` ~ `"06:00"` → 밤 10시부터 다음날 오전 6시까지

#### target_utilization

- 범위: `1` ~ `100` (정수 또는 소수)
- GPU SM(Streaming Multiprocessor) 사용률 기준

#### gpus

- `"all"`: 시스템의 모든 GPU 사용
- `[0]`: GPU 0번만 사용
- `[0, 2, 3]`: 특정 GPU만 선택

#### control

| 항목 | 설명 | 기본값 | 조정 기준 |
|------|------|--------|-----------|
| `interval_seconds` | 측정/조절 주기 | `1.0` | 낮추면 반응 빠름, CPU 부하 증가 |
| `pid_kp` | 비례 게인 | `0.01` | 높이면 반응 빠르지만 진동 가능 |
| `pid_ki` | 적분 게인 | `0.005` | 높이면 정상상태 오차 빨리 제거 |
| `pid_kd` | 미분 게인 | `0.002` | 높이면 진동 억제 강화 |
| `matrix_size` | 행렬 크기 (NxN) | `4096` | 클수록 GPU 점유 높음 |
| `cycle_period` | duty-cycle 1주기 | `0.1` (100ms) | 짧을수록 세밀한 제어 |

---

## 4. 실행

### 기본 실행

```bash
source venv/bin/activate
python -m gpu_controller --config config.yaml
```

### CLI 옵션

```
사용법: python -m gpu_controller [옵션]

옵션:
  --config, -c PATH     설정 파일 경로 (기본: config.yaml)
  --dry-run             설정만 검증하고 종료 (GPU 부하 없음)
  --once                제어 루프 1회만 실행 후 종료
  --log-level LEVEL     로그 레벨 오버라이드 (DEBUG/INFO/WARNING/ERROR)
```

### 실행 예시

```bash
# 설정 검증만 (GPU에 부하 걸리지 않음)
python -m gpu_controller --config config.yaml --dry-run

# DEBUG 로그로 실행 (PID 상태 출력)
python -m gpu_controller -c config.yaml --log-level DEBUG

# 1회만 실행 후 종료 (동작 확인용)
python -m gpu_controller --once

# 백그라운드 실행
nohup python -m gpu_controller -c config.yaml > /dev/null 2>&1 &
echo $!  # PID 확인
```

### systemd 서비스 등록 (선택)

`/etc/systemd/system/gpu-controller.service`:

```ini
[Unit]
Description=GPU Utilization Controller
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/GPU_OverWork
ExecStart=/path/to/GPU_OverWork/venv/bin/python -m gpu_controller --config config.yaml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable gpu-controller
sudo systemctl start gpu-controller
sudo systemctl status gpu-controller    # 상태 확인
sudo journalctl -u gpu-controller -f    # 로그 확인
```

---

## 5. 모니터링

### 로그 확인

```bash
# 실시간 로그
tail -f gpu_controller.log

# DEBUG 레벨에서 확인 가능한 정보:
# - GPU별 현재 사용률, 목표 사용률, duty_cycle, PID error
```

로그 출력 예시:
```
2025-02-25 18:00:01 [INFO] gpu_controller.runner: 활성 구간 진입 — 워크로드 시작
2025-02-25 18:00:02 [DEBUG] gpu_controller.runner: GPU 0: util=45.0% target=70.0% dc=0.700 err=25.0
2025-02-25 18:00:03 [DEBUG] gpu_controller.runner: GPU 0: util=62.0% target=70.0% dc=0.620 err=8.0
2025-02-25 18:00:10 [DEBUG] gpu_controller.runner: GPU 0: util=69.0% target=70.0% dc=0.548 err=1.0
2025-02-25 23:59:00 [INFO] gpu_controller.runner: 비활성 구간 — 워크로드 중지
```

### nvidia-smi로 GPU 상태 확인

```bash
# 1초 간격 사용률 모니터링
nvidia-smi dmon -s u -d 1

# 전체 정보 반복 출력
watch -n 1 nvidia-smi

# 특정 GPU만
nvidia-smi -i 0 --query-gpu=utilization.gpu,temperature.gpu,power.draw --format=csv -l 1
```

---

## 6. 종료

### 포그라운드 실행 중일 때

`Ctrl+C` 입력 → SIGINT 시그널로 graceful shutdown이 실행됩니다.

### 백그라운드 실행 중일 때

```bash
# PID를 알고 있다면
kill <PID>

# 프로세스 찾아서 종료
pkill -f "python -m gpu_controller"
```

### systemd 서비스일 때

```bash
sudo systemctl stop gpu-controller
```

### 종료 시 동작 순서

1. 시그널 수신 (SIGINT 또는 SIGTERM)
2. 각 GPU의 워크로드 스레드 중지
3. GPU 메모리(행렬) 해제 + `torch.cuda.empty_cache()`
4. NVML 종료
5. 프로세스 종료

> **참고**: `SIGKILL`(`kill -9`)은 graceful shutdown을 건너뛰므로
> GPU 메모리가 즉시 해제되지 않을 수 있습니다. 가급적 `SIGTERM`을 사용하세요.

---

## 7. 운영 시나리오별 설정 예시

### 야간 70% 유지 (기본)

```yaml
schedule:
  start_time: "18:00"
  end_time: "06:00"
target_utilization: 70
gpus: "all"
```

### 24시간 상시 가동

```yaml
schedule:
  start_time: "00:00"
  end_time: "23:59"
target_utilization: 50
```

### 특정 GPU만 높은 사용률

```yaml
gpus: [0, 1]
target_utilization: 90
control:
  matrix_size: 8192    # 더 큰 행렬로 높은 부하
```

### 낮은 사용률 유지 (워밍업용)

```yaml
target_utilization: 20
control:
  matrix_size: 2048    # 작은 행렬로 가벼운 부하
  cycle_period: 0.2    # 느린 주기
```

---

## 8. PID 튜닝 가이드

기본값(`kp=0.01, ki=0.005, kd=0.002`)은 대부분의 환경에서 안정적으로 동작합니다.
아래 경우에만 조정이 필요합니다.

### 증상별 조정

| 증상 | 원인 | 조정 |
|------|------|------|
| 목표에 도달이 너무 느림 | P/I 게인 부족 | `pid_kp` 1.5~2배 증가 |
| 목표 근처에서 진동 | P 게인 과다 | `pid_kp` 절반으로, `pid_kd` 소폭 증가 |
| 목표에 거의 도달하지만 오차 잔존 | I 게인 부족 | `pid_ki` 1.5배 증가 |
| 사용률이 크게 오버슈트 | D 게인 부족 | `pid_kd` 2배 증가 |

### 튜닝 절차

1. DEBUG 로그로 실행:
   ```bash
   python -m gpu_controller -c config.yaml --log-level DEBUG
   ```
2. 로그에서 `err=` 값 관찰 (목표 - 현재 사용률)
3. 10~30초 내에 `err`이 ±5 이내로 수렴하면 정상
4. 수렴하지 않으면 위 표를 참고하여 게인 조정

---

## 9. 트러블슈팅

### "CUDA를 사용할 수 없습니다"

```bash
# NVIDIA 드라이버 확인
nvidia-smi

# PyTorch CUDA 확인
python3 -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"
```

- 드라이버가 없으면: NVIDIA 드라이버 설치
- `torch.cuda.is_available()`이 `False`이면: CUDA 버전에 맞는 PyTorch 재설치

### "ModuleNotFoundError: No module named 'pynvml'"

```bash
source venv/bin/activate
pip install nvidia-ml-py
```

### CUDA OOM (Out of Memory)

프로그램이 자동으로 행렬 크기를 절반으로 축소합니다.
반복 발생 시 설정에서 `matrix_size`를 줄이세요:

```yaml
control:
  matrix_size: 2048    # 4096 → 2048
```

### GPU 인덱스 범위 초과

```bash
# 시스템 GPU 수 확인
nvidia-smi -L
```

설정에서 `gpus` 리스트의 인덱스가 실제 GPU 수를 넘지 않는지 확인하세요.

### 사용률이 목표에 도달하지 않음

- `matrix_size`를 증가 (4096 → 8192)
- `cycle_period`를 감소 (0.1 → 0.05)
- `target_utilization`이 100에 가까우면 물리적 한계일 수 있음

### 프로세스가 종료되지 않을 때

```bash
# graceful 종료 시도 (5초 대기)
kill $(pgrep -f "gpu_controller") && sleep 5

# 그래도 안 되면 강제 종료
kill -9 $(pgrep -f "gpu_controller")
```

---

## 10. 테스트

### 단위 테스트 (GPU 불필요)

```bash
source venv/bin/activate
pytest tests/test_config.py tests/test_controller.py tests/test_scheduler.py -v
```

### 통합 테스트 (GPU 필요)

```bash
pytest tests/test_monitor.py tests/test_workload.py -v
```

### 전체 테스트

```bash
pytest tests/ -v
```

### 시스템 테스트 (수동)

```bash
# 터미널 1: 컨트롤러 실행
python -m gpu_controller -c config.yaml --log-level DEBUG

# 터미널 2: GPU 모니터링
nvidia-smi dmon -s u -d 1
```

목표 사용률에 수렴하는지 확인합니다. 보통 10~30초 내 안정화됩니다.
