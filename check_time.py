"""현재 시스템 시간 확인 — 스케줄 설정 시 참고용."""

from datetime import datetime

now = datetime.now()
print(f"현재 시스템 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"config.yaml 설정용: \"{now.strftime('%H:%M')}\"")
