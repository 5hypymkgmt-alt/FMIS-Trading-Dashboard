"""Regression tests for FMIS completed daily candle filtering."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from update import filter_completed_daily_candles


def test_completed_candle_filter():
    cutoff = datetime.date(2026, 11, 5)

    candles = [
        {"datetime": "2026-11-04", "close": "4058"},
        {"datetime": "2026-11-05", "close": "4103"},
        {"datetime": "2026-11-06", "close": "4106"},
    ]

    result = filter_completed_daily_candles(candles, cutoff)

    assert [c["datetime"] for c in result] == ["2026-11-04"]


def test_minimum_completed_history():
    cutoff = datetime.date(2026, 11, 5)

    candles = [
        {
            "datetime": (
                cutoff - datetime.timedelta(days=i)
            ).isoformat()
        }
        for i in range(211)
    ]

    result = filter_completed_daily_candles(candles, cutoff)

    assert len(result) == 210


def test_future_and_current_candles_excluded():
    cutoff = datetime.date(2026, 11, 5)

    candles = [
        {"datetime": "2026-11-04"},
        {"datetime": "2026-11-05"},
        {"datetime": "2026-11-06"},
    ]

    result = filter_completed_daily_candles(candles, cutoff)

    assert all(
        datetime.date.fromisoformat(c["datetime"]) < cutoff
        for c in result
    )


if __name__ == "__main__":
    test_completed_candle_filter()
    print("PASS: Developing and future candles excluded")

    test_minimum_completed_history()
    print("PASS: 210 completed candles retained")

    test_future_and_current_candles_excluded()
    print("PASS: Future-date regression test")

    print("PASS: All completed-candle regression tests")
