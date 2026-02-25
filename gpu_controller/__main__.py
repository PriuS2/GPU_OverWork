"""CLI 진입점: python -m gpu_controller"""

import argparse
import signal
import sys
import logging

from .config import load_config
from .logging_config import setup_logging
from .runner import Runner

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gpu_controller",
        description="GPU 사용률을 목표 %로 유지하는 컨트롤러",
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="설정 파일 경로 (기본: config.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="설정만 로드하고 종료",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="제어 루프 1회만 실행 후 종료",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="로그 레벨 (설정 파일보다 우선)",
    )
    args = parser.parse_args()

    # 설정 로드
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"설정 오류: {e}", file=sys.stderr)
        sys.exit(1)

    # CLI에서 log-level 오버라이드
    if args.log_level:
        config["log_level"] = args.log_level

    setup_logging(config["log_file"], config["log_level"])

    logger.info("설정 로드 완료: %s", args.config)
    logger.info(
        "스케줄: %s ~ %s, 목표: %s%%, GPU: %s",
        config["schedule"]["start_time"],
        config["schedule"]["end_time"],
        config["target_utilization"],
        config["gpus"],
    )

    if args.dry_run:
        logger.info("Dry-run 모드 - 설정 확인 후 종료")
        return

    # CUDA 확인
    try:
        import torch
        if not torch.cuda.is_available():
            logger.error("CUDA를 사용할 수 없습니다. NVIDIA GPU와 CUDA 드라이버를 확인하세요.")
            sys.exit(1)
        logger.info("CUDA 사용 가능 - GPU: %s", torch.cuda.get_device_name(0))
    except ImportError:
        logger.error("PyTorch가 설치되지 않았습니다.")
        sys.exit(1)

    # Runner 생성 + 시그널 핸들러
    runner = Runner(config)

    def _signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info("시그널 수신: %s - 종료 시작", sig_name)
        runner.shutdown()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # 실행
    try:
        runner.run(once=args.once)
    except KeyboardInterrupt:
        runner.shutdown()
    except Exception:
        logger.exception("예기치 않은 오류 발생")
        sys.exit(1)


if __name__ == "__main__":
    main()
