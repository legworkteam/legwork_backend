from datetime import UTC, datetime, timezone, timedelta


KST = timezone(timedelta(hours=9), name="KST")


def now_kst() -> datetime:
    return datetime.now(UTC).astimezone(KST)
