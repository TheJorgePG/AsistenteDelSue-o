from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.progress import DailySleepLogModel, UserProfileModel


def serialize_profile(profile: UserProfileModel | None) -> dict | None:
    if profile is None:
        return None
    return {
        "display_name": profile.display_name,
        "age_range": profile.age_range,
        "sleep_goal_hours": profile.sleep_goal_hours,
        "timezone": profile.timezone,
    }


def serialize_sleep_log(log: DailySleepLogModel) -> dict:
    return {
        "id": log.id,
        "sleep_date": log.sleep_date.isoformat(),
        "hours_slept": log.hours_slept,
        "quality_score": log.quality_score,
        "awakenings": log.awakenings,
    }


def build_gamification(
    logs: list[DailySleepLogModel],
    profile: UserProfileModel | None,
) -> dict:
    dates = {log.sleep_date for log in logs}
    timezone_name = profile.timezone if profile else "UTC"
    today = datetime.now(ZoneInfo(timezone_name)).date()
    streak_start = today if today in dates else today - timedelta(days=1)
    streak = 0
    while streak_start in dates:
        streak += 1
        streak_start -= timedelta(days=1)

    total_nights = len(dates)
    badges = [
        {
            "id": "first-night",
            "title": "Primer paso",
            "description": "Registra tu primera noche.",
            "unlocked": total_nights >= 1,
            "progress": min(total_nights, 1),
            "target": 1,
        },
        {
            "id": "week-streak",
            "title": "Una semana constante",
            "description": "Registra siete noches seguidas.",
            "unlocked": streak >= 7,
            "progress": min(streak, 7),
            "target": 7,
        },
        {
            "id": "thirty-nights",
            "title": "Treinta noches",
            "description": "Completa treinta registros de sueño.",
            "unlocked": total_nights >= 30,
            "progress": min(total_nights, 30),
            "target": 30,
        },
    ]
    return {
        "points": total_nights * 10,
        "current_streak": streak,
        "nights_logged": total_nights,
        "badges": badges,
    }


def build_dashboard(
    profile: UserProfileModel | None,
    logs: list[DailySleepLogModel],
) -> dict:
    ordered_logs = sorted(logs, key=lambda log: log.sleep_date)
    return {
        "profile": serialize_profile(profile),
        "sleep_goal_hours": profile.sleep_goal_hours if profile else 8.0,
        "sleep_logs": [serialize_sleep_log(log) for log in ordered_logs],
        "gamification": build_gamification(logs, profile),
    }
