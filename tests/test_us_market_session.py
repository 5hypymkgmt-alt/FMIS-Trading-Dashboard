"""Independent FMIS US equity session-boundary tests."""

import datetime
from zoneinfo import ZoneInfo

UTC = datetime.timezone.utc
NEW_YORK = ZoneInfo("America/New_York")

def us_session_complete(candle_date, now_utc):
    """Candidate regular-session close at 16:00 New York time."""
    session_date = datetime.date.fromisoformat(candle_date)
    session_end = datetime.datetime.combine(
        session_date,
        datetime.time(16, 0),
        tzinfo=NEW_YORK,
    )
    return now_utc >= session_end.astimezone(UTC)

# Winter: 16:00 EST = 21:00 UTC.
assert not us_session_complete(
    "2026-01-15",
    datetime.datetime(2026, 1, 15, 20, 59, tzinfo=UTC),
)
assert us_session_complete(
    "2026-01-15",
    datetime.datetime(2026, 1, 15, 21, 1, tzinfo=UTC),
)

# Summer: 16:00 EDT = 20:00 UTC.
assert not us_session_complete(
    "2026-07-15",
    datetime.datetime(2026, 7, 15, 19, 59, tzinfo=UTC),
)
assert us_session_complete(
    "2026-07-15",
    datetime.datetime(2026, 7, 15, 20, 1, tzinfo=UTC),
)

print("PASS: Winter US market session boundary")
print("PASS: Summer US market session boundary")
