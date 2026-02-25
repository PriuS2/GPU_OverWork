"""로깅 설정."""

import logging
import sys


def setup_logging(log_file: str = "gpu_controller.log", log_level: str = "INFO") -> None:
    """파일 + 콘솔 로깅 설정."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # 기존 핸들러 제거
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 파일 핸들러
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError as e:
        root.warning("로그 파일 생성 실패: %s - 콘솔만 사용", e)
