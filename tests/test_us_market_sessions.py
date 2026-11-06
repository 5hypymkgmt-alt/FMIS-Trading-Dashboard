"""Independent NYSE session tests for SPY and QQQ."""

import datetime
import exchange_calendars as xc

from update import filter_completed_session_candles

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


def test_candle_selection_before_and_after_close():
    before = datetime.datetime(
        2026, 11, 2, 21, 10, tzinfo=UTC
    )
    after = datetime.datetime(
        2026, 11, 2, 21, 16, tzinfo=UTC
    )

    candles = [
        {"datetime": "2026-11-02", "close": "4100"},
        {"datetime": "2026-11-03", "close": "4150"},
    ]

    assert len(filter_completed_session_candles(
        candles, before
    )) == 0

    result = filter_completed_session_candles(
        candles, after
    )

    assert [c["datetime"] for c in result] == [
        "2026-11-02"
    ]

    print("PASS: Session-aware candle selection")
def test_candle_selection_on_early_close():
    before = datetime.datetime(
        2026, 11, 27, 18, 10, tzinfo=UTC
    )
    after = datetime.datetime(
        2026, 11, 27, 18, 16, tzinfo=UTC
    )

    candles = [
        {"datetime": "2026-11-27", "close": "4100"},
    ]

    assert len(filter_completed_session_candles(
        candles, before
    )) == 0

    result = filter_completed_session_candles(
        candles, after
    )

    assert len(result) == 1

    print("PASS: Early-close candle selection")
if __name__ == "__main__":
    test_winter_session()
    test_summer_session()
    test_early_close()
    test_holiday_and_weekend()
    test_candle_selection_before_and_after_close()
    test_candle_selection_on_early_close()
    print("PASS: All NYSE session tests")
