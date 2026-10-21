from datetime import date
from zoneinfo import ZoneInfo

from app.booking.seed import slot_times

TZ = ZoneInfo("Asia/Tashkent")
HOURS = {"weekday": ["09:00", "18:00"], "sunday": ["09:00", "14:00"]}


def test_weekday_and_sunday_hours() -> None:
    monday = date(2026, 10, 19)
    sunday = date(2026, 10, 25)
    mon = slot_times(monday, 1, HOURS, 30, TZ)
    sun = slot_times(sunday, 1, HOURS, 30, TZ)
    assert len(mon) == 18 and mon[0].hour == 9 and mon[-1].strftime("%H:%M") == "17:30"
    assert len(sun) == 10 and sun[-1].strftime("%H:%M") == "13:30"


def test_long_services_fit_inside_hours() -> None:
    times = slot_times(date(2026, 10, 19), 1, HOURS, 90, TZ)
    assert times[-1].strftime("%H:%M") == "16:30"  # 16:30 + 90 min = 18:00
