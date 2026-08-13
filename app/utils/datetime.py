from datetime import UTC, datetime, timezone, timedelta


KST = timezone(timedelta(hours=9), name="KST")


def now_kst() -> datetime:
    return datetime.now(UTC).astimezone(KST)


def end_of_day_kst(moment: datetime | None = None) -> datetime:
    """23:59:59.999999 KST of the given moment's day (default: today)."""
    base = (moment or now_kst()).astimezone(KST)
    return base.replace(hour=23, minute=59, second=59, microsecond=999999)
