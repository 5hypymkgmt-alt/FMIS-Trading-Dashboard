"""Independent NYSE session tests for SPY and QQQ."""

import datetime
import exchange_calendars as xc

UTC = datetime.timezone.utc
calendar = xc.get_calendar("XNYS")


def session_complete(day, now_utc, delay_minutes=15):
    """Check exchange close plus a provisional safety delay."""
    if not calendar.is_session(day):
        return False

    close = calendar.session_close(day).to_pydatetime()
    ready_at = close + datetime.timedelta(minutes=delay_minutes)

    return now_utc >= ready_at


def test_winter_session():
    before = datetime.datetime(2026, 11, 2, 21, 10, tzinfo=UTC)
    after = datetime.datetime(2026, 11, 2, 21, 16, tzinfo=UTC)

    assert not session_complete("2026-11-02", before)
    assert session_complete("2026-11-02", after)


def test_summer_session():
    after = datetime.datetime(2026, 7, 2, 20, 16, tzinfo=UTC)
    assert session_complete("2026-07-02", after)


def test_early_close():
    after = datetime.datetime(2026, 11, 27, 18, 16, tzinfo=UTC)
    assert session_complete("2026-11-27", after)


def test_holiday_and_weekend():
    now = datetime.datetime(2026, 11, 30, 22, 0, tzinfo=UTC)

    assert not session_complete("2026-11-26", now)
    assert not session_complete("2026-11-28", now)


if __name__ == "__main__":
    test_winter_session()
    test_summer_session()
    test_early_close()
    test_holiday_and_weekend()
    print("PASS: All NYSE session tests")
