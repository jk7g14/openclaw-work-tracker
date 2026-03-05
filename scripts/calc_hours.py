#!/usr/bin/env python3
"""근무시간 계산 엔진 - 점심 차감, 추천 스케줄 생성"""

import argparse
import json
import sys
from datetime import datetime, timedelta

WEEKLY_HOURS = 40
LUNCH_START = (12, 30)
LUNCH_END = (13, 30)
LUNCH_MINUTES = 60
CORE_START = (11, 0)
CORE_END = (17, 0)
HALF_DAY_CREDIT = 4.0
VACATION_CREDIT = 8.0
FRIDAY_LEAVE = (17, 0)  # 금요일 고정 퇴근


def to_minutes(h, m):
    return h * 60 + m


def parse_time(s):
    """'HH:MM' or 'H:MM' -> (hour, minute)"""
    parts = s.strip().split(":")
    return int(parts[0]), int(parts[1])


def lunch_overlap_minutes(start_hm, end_hm):
    """출근~퇴근 시간과 점심(12:30~13:30) 겹치는 분 계산"""
    s = to_minutes(*start_hm)
    e = to_minutes(*end_hm)
    ls = to_minutes(*LUNCH_START)
    le = to_minutes(*LUNCH_END)
    overlap_start = max(s, ls)
    overlap_end = min(e, le)
    return max(0, overlap_end - overlap_start)


def calc_day_hours(day):
    """하루 실근무시간(시간 단위) 계산.

    day: {
      "date": "2026-03-02",
      "day_of_week": "Mon",
      "status": "normal" | "half" | "vacation" | "holiday" | "today",
      "clock_in": "09:00",   # optional
      "clock_out": "18:00",  # optional (today면 없음)
    }
    """
    status = day.get("status", "normal")

    if status in ("holiday", "공휴일"):
        return {"status": "holiday", "worked": 0, "credit": 0}

    if status in ("vacation", "휴가"):
        return {"status": "vacation", "worked": 0, "credit": VACATION_CREDIT}

    clock_in = day.get("clock_in")
    clock_out = day.get("clock_out")

    if status in ("half", "반차"):
        # 반차: 4시간 크레딧 + 실근무시간
        credit = HALF_DAY_CREDIT
        if clock_in and clock_out:
            start = parse_time(clock_in)
            end = parse_time(clock_out)
            total_min = to_minutes(*end) - to_minutes(*start)
            lunch_min = lunch_overlap_minutes(start, end)
            worked = max(0, total_min - lunch_min) / 60
        else:
            worked = 0
        return {"status": "half", "worked": round(worked, 2), "credit": round(credit + worked, 2)}

    if status == "today":
        # 오늘: 출근만 있음, 퇴근 추천 필요
        if clock_in:
            return {"status": "today", "clock_in": clock_in, "worked": None, "credit": None}
        return {"status": "today", "worked": None, "credit": None}

    # normal
    if not clock_in or not clock_out:
        return {"status": "normal", "worked": 0, "credit": 0}

    start = parse_time(clock_in)
    end = parse_time(clock_out)
    total_min = to_minutes(*end) - to_minutes(*start)
    lunch_min = lunch_overlap_minutes(start, end)
    worked = max(0, total_min - lunch_min) / 60
    return {"status": "normal", "worked": round(worked, 2), "credit": round(worked, 2)}


def recommend_clock_out(clock_in_str, needed_hours):
    """출근시간 + 필요시간 -> 퇴근시간 추천 (점심 차감 반영)"""
    start = parse_time(clock_in_str)
    start_min = to_minutes(*start)

    # 필요 근무분 + 점심 겹침 예측
    needed_min = needed_hours * 60
    # 먼저 점심 없이 계산
    raw_end = start_min + needed_min
    # 점심 겹침 확인 후 보정
    lunch_s = to_minutes(*LUNCH_START)
    lunch_e = to_minutes(*LUNCH_END)

    if start_min < lunch_e and raw_end > lunch_s:
        # 점심시간과 겹침 -> 점심시간만큼 추가
        overlap = min(raw_end, lunch_e) - max(start_min, lunch_s)
        overlap = max(0, overlap)
        raw_end += overlap
        # 보정 후 다시 체크 (점심 추가로 더 겹칠 수 있음)
        new_overlap = min(raw_end, lunch_e) - max(start_min, lunch_s)
        new_overlap = max(0, new_overlap)
        if new_overlap > overlap:
            raw_end += (new_overlap - overlap)

    h, m = divmod(int(raw_end), 60)
    return f"{h:02d}:{m:02d}"


def generate_recommendations(today_info, remaining_hours, remaining_days):
    """추천 출퇴근 옵션 생성.

    today_info: 오늘 데이터 (clock_in 포함)
    remaining_hours: 이번 주 남은 필요 시간
    remaining_days: 오늘 포함 남은 근무일 리스트 [{"date":..., "day_of_week":...}, ...]
    """
    recommendations = []

    if not remaining_days or remaining_hours <= 0:
        return recommendations

    today = remaining_days[0] if remaining_days else None
    future_days = remaining_days[1:] if len(remaining_days) > 1 else []

    # 금요일 체크: 남은 날 중 금요일이 있으면 해당 날은 17:00 퇴근 고정
    # 금요일 근무시간 = 출근~17:00 - 점심
    def friday_fixed_hours(clock_in_str):
        start = parse_time(clock_in_str)
        end = FRIDAY_LEAVE
        total_min = to_minutes(*end) - to_minutes(*start)
        lunch_min = lunch_overlap_minutes(start, end)
        return max(0, total_min - lunch_min) / 60

    # 옵션 1: 균등 분배
    hours_per_day = remaining_hours / len(remaining_days)

    opt1_schedule = []
    hours_left = remaining_hours

    for d in remaining_days:
        dow = d.get("day_of_week", "")
        is_friday = dow in ("Fri", "금")
        is_today = d.get("date") == (today_info or {}).get("date") if today_info else False
        clock_in = today_info.get("clock_in", "09:00") if is_today and today_info else "09:00"

        if is_friday:
            # 금요일: 17:00 퇴근 고정
            fri_hours = friday_fixed_hours(clock_in)
            clock_out = f"{FRIDAY_LEAVE[0]:02d}:{FRIDAY_LEAVE[1]:02d}"
            opt1_schedule.append({
                "date": d["date"], "day_of_week": dow,
                "clock_in": clock_in, "clock_out": clock_out,
                "hours": round(fri_hours, 2)
            })
            hours_left -= fri_hours
        else:
            opt1_schedule.append({
                "date": d["date"], "day_of_week": dow,
                "clock_in": clock_in, "hours": None  # placeholder
            })

    # 금요일 제외 남은 날에 시간 분배
    non_friday = [s for s in opt1_schedule if s["hours"] is None]
    if non_friday:
        per_day = max(0, hours_left / len(non_friday))
        for s in non_friday:
            s["hours"] = round(per_day, 2)
            s["clock_out"] = recommend_clock_out(s["clock_in"], per_day)

    recommendations.append({
        "option": "균등 분배",
        "description": "남은 근무일에 균등하게 시간 분배 (금요일 17시 퇴근 고정)",
        "schedule": opt1_schedule
    })

    # 옵션 2: 오늘 일찍, 나머지 약간 더
    if len(remaining_days) >= 2 and today_info and today_info.get("clock_in"):
        opt2_schedule = []
        hours_left2 = remaining_hours

        # 오늘은 코어타임 끝(17:00)에 퇴근
        today_clock_in = today_info["clock_in"]
        today_end = CORE_END
        today_total = to_minutes(*today_end) - to_minutes(*parse_time(today_clock_in))
        today_lunch = lunch_overlap_minutes(parse_time(today_clock_in), today_end)
        today_hours = max(0, today_total - today_lunch) / 60
        today_dow = remaining_days[0].get("day_of_week", "")
        is_today_friday = today_dow in ("Fri", "금")

        if is_today_friday:
            today_hours_final = today_hours
        else:
            today_hours_final = today_hours

        opt2_schedule.append({
            "date": remaining_days[0]["date"], "day_of_week": today_dow,
            "clock_in": today_clock_in,
            "clock_out": f"{today_end[0]:02d}:{today_end[1]:02d}",
            "hours": round(today_hours_final, 2)
        })
        hours_left2 -= today_hours_final

        for d in future_days:
            dow = d.get("day_of_week", "")
            is_friday = dow in ("Fri", "금")
            clock_in = "09:00"

            if is_friday:
                fri_hours = friday_fixed_hours(clock_in)
                opt2_schedule.append({
                    "date": d["date"], "day_of_week": dow,
                    "clock_in": clock_in,
                    "clock_out": f"{FRIDAY_LEAVE[0]:02d}:{FRIDAY_LEAVE[1]:02d}",
                    "hours": round(fri_hours, 2)
                })
                hours_left2 -= fri_hours
            else:
                opt2_schedule.append({
                    "date": d["date"], "day_of_week": dow,
                    "clock_in": clock_in, "hours": None
                })

        non_friday2 = [s for s in opt2_schedule[1:] if s["hours"] is None]
        if non_friday2:
            per_day2 = max(0, hours_left2 / len(non_friday2))
            for s in non_friday2:
                s["hours"] = round(per_day2, 2)
                s["clock_out"] = recommend_clock_out(s["clock_in"], per_day2)

        recommendations.append({
            "option": "오늘 코어타임 퇴근",
            "description": "오늘 17시 퇴근, 나머지 날에 분배 (금요일 17시 고정)",
            "schedule": opt2_schedule
        })

    # 옵션 3: 오늘 많이, 나머지 여유
    if len(remaining_days) >= 2 and today_info and today_info.get("clock_in"):
        opt3_schedule = []
        hours_left3 = remaining_hours

        # 나머지 날 8시간씩 잡고, 오늘 나머지
        future_total = 0
        temp_future = []
        for d in future_days:
            dow = d.get("day_of_week", "")
            is_friday = dow in ("Fri", "금")
            clock_in = "09:00"
            if is_friday:
                fri_h = friday_fixed_hours(clock_in)
                temp_future.append({
                    "date": d["date"], "day_of_week": dow,
                    "clock_in": clock_in,
                    "clock_out": f"{FRIDAY_LEAVE[0]:02d}:{FRIDAY_LEAVE[1]:02d}",
                    "hours": round(fri_h, 2)
                })
                future_total += fri_h
            else:
                default_h = 8.0
                temp_future.append({
                    "date": d["date"], "day_of_week": dow,
                    "clock_in": clock_in,
                    "clock_out": recommend_clock_out(clock_in, default_h),
                    "hours": default_h
                })
                future_total += default_h

        today_needed = max(0, hours_left3 - future_total)
        today_clock_in = today_info["clock_in"]

        opt3_schedule.append({
            "date": remaining_days[0]["date"], "day_of_week": remaining_days[0].get("day_of_week", ""),
            "clock_in": today_clock_in,
            "clock_out": recommend_clock_out(today_clock_in, today_needed),
            "hours": round(today_needed, 2)
        })
        opt3_schedule.extend(temp_future)

        recommendations.append({
            "option": "오늘 몰아서 + 나머지 8시간",
            "description": "나머지 날 8시간 기준, 부족분을 오늘 채움 (금요일 17시 고정)",
            "schedule": opt3_schedule
        })

    return recommendations


def main():
    parser = argparse.ArgumentParser(description="주간 근무시간 계산기")
    parser.add_argument("--data", required=True, help="JSON 데이터")
    args = parser.parse_args()

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON 파싱 오류: {e}"}, ensure_ascii=False))
        sys.exit(1)

    days = data.get("days", [])
    results = []
    total_credit = 0
    today_info = None
    remaining_days = []
    found_today = False

    for day in days:
        r = calc_day_hours(day)
        r["date"] = day.get("date", "")
        r["day_of_week"] = day.get("day_of_week", "")

        if r["status"] == "today":
            today_info = {**day, **r}
            found_today = True
            remaining_days.append(day)
        elif r["status"] == "holiday":
            pass  # 공휴일은 무시
        elif found_today is False:
            # 오늘 이전 완료일
            total_credit += r.get("credit", 0)
        else:
            # 오늘 이후 미래 근무일
            remaining_days.append(day)

        if r["status"] != "today":
            results.append(r)
        else:
            results.append(r)

    remaining_hours = max(0, WEEKLY_HOURS - total_credit)
    recommendations = generate_recommendations(today_info, remaining_hours, remaining_days)

    output = {
        "daily": results,
        "total_credited": round(total_credit, 2),
        "weekly_target": WEEKLY_HOURS,
        "remaining_hours": round(remaining_hours, 2),
        "recommendations": recommendations
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
