import datetime

import pandas as pd


def normalize_period(
    start_date: datetime.date | str,
    end_date: datetime.date | str | None = None,
    *,
    include_start: bool = False,
) -> tuple[datetime.date, datetime.date]:
    start = pd.Timestamp(start_date).date()
    end = datetime.date.today() if end_date is None else pd.Timestamp(end_date).date()
    if end < start:
        raise ValueError("end_date must be greater than or equal to start_date")
    if not include_start:
        start = start + datetime.timedelta(days=1)
    return start, end


def calculate_days_since(
    start_date: datetime.date | str,
    end_date: datetime.date | str | None = None,
) -> int:
    start = pd.Timestamp(start_date).date()
    end = datetime.date.today() if end_date is None else pd.Timestamp(end_date).date()
    if end < start:
        raise ValueError("end_date must be greater than or equal to start_date")
    return (end - start).days
