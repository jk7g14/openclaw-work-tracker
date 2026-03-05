# openclaw-work-tracker

다우오피스 사용자를 위한 OpenClaw 근무시간 추적 스킬.

텔레그램으로 출퇴근 기록 사진을 보내면 AI가 이미지를 분석하고, 주간 근무현황과 추천 퇴근시간을 알려줍니다.

## 기능

- 출퇴근 사진에서 시간 자동 추출 (GPT 비전)
- 점심시간(12:30~13:30) 자동 차감
- 반차(4h 인정) / 휴가(8h 인정) / 공휴일 처리
- 주 40시간 기준 남은 시간 계산
- 추천 퇴근 스케줄 2~3개 제시
- 금요일 17시 퇴근 고정 옵션

## 회사 규칙 (기본값)

| 항목 | 값 |
|------|-----|
| 주간 근무시간 | 40시간 |
| 코어타임 | 11:00 ~ 17:00 |
| 점심시간 | 12:30 ~ 13:30 (무조건 차감) |
| 반차 | 4시간 인정 |
| 휴가 | 8시간 인정 |

## 설치

```bash
# 1. 클론
git clone https://github.com/your-username/openclaw-work-tracker.git

# 2. OpenClaw 스킬 디렉토리에 복사
cp -r openclaw-work-tracker ~/.openclaw/workspace/skills/work-tracker

# 3. 게이트웨이 재시작
openclaw gateway restart
```

또는 install 스크립트 사용:

```bash
./install.sh
```

## 단독 테스트

```bash
python3 scripts/calc_hours.py --data '{
  "days": [
    {"date": "2026-03-02", "day_of_week": "Mon", "status": "normal", "clock_in": "09:15", "clock_out": "18:20"},
    {"date": "2026-03-03", "day_of_week": "Tue", "status": "normal", "clock_in": "10:00", "clock_out": "19:05"},
    {"date": "2026-03-04", "day_of_week": "Wed", "status": "half", "clock_in": "13:30", "clock_out": "17:00"},
    {"date": "2026-03-05", "day_of_week": "Thu", "status": "today", "clock_in": "09:30"},
    {"date": "2026-03-06", "day_of_week": "Fri", "status": "normal"}
  ]
}'
```

## 커스터마이즈

`scripts/calc_hours.py` 상단의 상수를 수정하여 회사 규칙을 변경할 수 있습니다:

```python
WEEKLY_HOURS = 40
LUNCH_START = (12, 30)
LUNCH_END = (13, 30)
CORE_START = (11, 0)
CORE_END = (17, 0)
HALF_DAY_CREDIT = 4.0
VACATION_CREDIT = 8.0
FRIDAY_LEAVE = (17, 0)
```

## 사용법

1. 텔레그램에서 OpenClaw 봇에게 다우오피스 출퇴근 기록 스크린샷을 전송
2. 봇이 이미지를 분석하여 출퇴근 시간 추출
3. 주간 근무현황 테이블 + 추천 퇴근 스케줄 응답

## 라이선스

MIT
