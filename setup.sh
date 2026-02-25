#!/bin/bash
set -e

echo "=== GPU Utilization Controller 환경 설정 ==="

# python3-venv / ensurepip 확인 및 설치
if ! python3 -c "import ensurepip" 2>/dev/null; then
    echo ">> python3-venv 패키지 설치..."
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    sudo apt update && sudo apt install -y "python${PY_VER}-venv"
fi

# venv 생성
if [ ! -d "venv" ]; then
    echo ">> Python venv 생성..."
    python3 -m venv venv
else
    echo ">> 기존 venv 발견 — 재사용"
fi

# 활성화
source venv/bin/activate

# pip 업그레이드
echo ">> pip 업그레이드..."
pip install --upgrade pip

# PyTorch (CUDA 12.6)
echo ">> PyTorch 설치 (CUDA 12.6)..."
pip install torch --index-url https://download.pytorch.org/whl/cu126

# 기타 의존성
echo ">> 의존성 설치..."
pip install nvidia-ml-py PyYAML

# 테스트 도구
echo ">> 테스트 도구 설치..."
pip install pytest pytest-cov

# config.yaml 생성 (없으면)
if [ ! -f "config.yaml" ]; then
    echo ">> config.example.yaml → config.yaml 복사"
    cp config.example.yaml config.yaml
fi

echo ""
echo "=== 설정 완료 ==="
echo "사용법:"
echo "  source venv/bin/activate"
echo "  python -m gpu_controller --config config.yaml"
