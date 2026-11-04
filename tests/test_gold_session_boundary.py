"""Independent tests for the suspected Gold daily session boundary."""

import datetime

UTC = datetime.timezone.utc

def gold_session_complete(candle_date, now_utc):
    """Test candidate 20:00 UTC session completion rule."""
    session_end = datetime.datetime.combine(
        datetime.date.fromisoformat(candle_date),
        datetime.time(20, 0),
        tzinfo=UTC,
    )
    return now_utc >= session_end

before = datetime.datetime(2026, 11, 4, 19, 59, tzinfo=UTC)
after = datetime.datetime(2026, 11, 4, 20, 1, tzinfo=UTC)

assert not gold_session_complete("2026-11-04", before)
assert gold_session_complete("2026-11-04", after)
assert gold_session_complete("2026-11-03", before)

print("PASS: Current Gold candle excluded before 20:00 UTC")
print("PASS: Current Gold candle eligible after 20:00 UTC")
print("PASS: Previous Gold candle remains eligible")
