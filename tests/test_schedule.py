import importlib
import os
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

import config.config as config_module
from scheduler import calculate_next_run_time


def reload_config():
    return importlib.reload(config_module).config


def test_calculate_next_run_before_schedule():
    schedule = reload_config().schedule
    tz = pytz.timezone(schedule.timezone)
    now = tz.localize(datetime(2024, 1, 1, schedule.hour - 1, 30))

    next_run = calculate_next_run_time(schedule, now)

    assert next_run.date() == now.date()
    assert next_run.hour == schedule.hour
    assert next_run.minute == schedule.minute


def test_calculate_next_run_after_schedule():
    schedule = reload_config().schedule
    tz = pytz.timezone(schedule.timezone)
    now = tz.localize(datetime(2024, 1, 1, schedule.hour + 2, 0))

    next_run = calculate_next_run_time(schedule, now)

    expected_date = (now + timedelta(days=1)).date()

    assert next_run.date() == expected_date
    assert next_run.hour == schedule.hour
    assert next_run.minute == schedule.minute


def test_run_on_start_flag_respects_env():
    original_value = os.environ.get("RUN_ON_START")
    try:
        os.environ["RUN_ON_START"] = "false"
        config = reload_config()
        assert config.schedule.run_on_start is False
    finally:
        if original_value is None:
            os.environ.pop("RUN_ON_START", None)
        else:
            os.environ["RUN_ON_START"] = original_value
        reload_config()
