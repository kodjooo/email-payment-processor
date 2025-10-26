"""Вспомогательные функции для расчёта расписания ежедневного запуска."""
from datetime import datetime, timedelta
from typing import Optional

import pytz


def calculate_next_run_time(schedule_config, current_time: Optional[datetime] = None) -> datetime:
    """Рассчитать дату и время следующего запуска с учётом часового пояса."""
    tz = pytz.timezone(schedule_config.timezone)

    if current_time is None:
        current_time = datetime.now(tz)
    else:
        if current_time.tzinfo is None:
            current_time = tz.localize(current_time)
        else:
            current_time = current_time.astimezone(tz)

    scheduled_time = datetime(
        current_time.year,
        current_time.month,
        current_time.day,
        schedule_config.hour,
        schedule_config.minute
    )
    scheduled_time = tz.localize(scheduled_time)

    if current_time >= scheduled_time:
        scheduled_time += timedelta(days=1)

    return scheduled_time
