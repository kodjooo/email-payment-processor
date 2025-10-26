import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytz


ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT_DIR / "email-processor"
SRC_DIR = PROJECT_DIR / "src"

for path in (SRC_DIR, PROJECT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from config.config import config
from scheduler import calculate_next_run_time


def test_calculate_next_run_before_schedule():
    schedule = config.schedule
    tz = pytz.timezone(schedule.timezone)
    now = tz.localize(datetime(2024, 1, 1, schedule.hour - 1, 30))

    next_run = calculate_next_run_time(schedule, now)

    assert next_run.date() == now.date()
    assert next_run.hour == schedule.hour
    assert next_run.minute == schedule.minute


def test_calculate_next_run_after_schedule():
    schedule = config.schedule
    tz = pytz.timezone(schedule.timezone)
    now = tz.localize(datetime(2024, 1, 1, schedule.hour + 2, 0))

    next_run = calculate_next_run_time(schedule, now)

    expected_date = (now + timedelta(days=1)).date()

    assert next_run.date() == expected_date
    assert next_run.hour == schedule.hour
    assert next_run.minute == schedule.minute
