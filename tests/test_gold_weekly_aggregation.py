"""Regression tests for completed Gold weekly candles."""

import unittest
from datetime import date

from gold_market_structure import aggregate_ohlc


def candle(day, opening, high, low, close):
    return {
        "datetime": day,
        "open": opening,
        "high": high,
        "low": low,
        "close": close,
    }


class GoldWeeklyAggregationTests(unittest.TestCase):

    def test_completed_week_ohlc_aggregation(self):
        daily = [
            candle("2026-10-26", 4000, 4050, 3980, 4020),
            candle("2026-10-28", 4020, 4100, 4000, 4080),
            candle("2026-10-30", 4080, 4120, 4050, 4100),
        ]

        result = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 11, 2)
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["datetime"], "2026-10-26")
        self.assertEqual(result[0]["open"], 4000)
        self.assertEqual(result[0]["high"], 4120)
        self.assertEqual(result[0]["low"], 3980)
        self.assertEqual(result[0]["close"], 4100)

    def test_developing_week_excluded(self):
        daily = [
            candle("2026-10-30", 4000, 4100, 3950, 4050),
            candle("2026-11-02", 4050, 4300, 4000, 4250),
            candle("2026-11-03", 4250, 4350, 4200, 4300),
        ]

        result = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 11, 4)
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["datetime"], "2026-10-26")

    def test_friday_week_available_on_saturday(self):
        daily = [
            candle("2026-10-30", 4000, 4100, 3950, 4050),
        ]

        friday = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 10, 30)
        )

        saturday = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 10, 31)
        )

        self.assertEqual(friday, [])
        self.assertEqual(len(saturday), 1)

    def test_weekend_does_not_create_extra_week(self):
        daily = [
            candle("2026-10-30", 4000, 4100, 3950, 4050),
        ]

        saturday = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 10, 31)
        )

        sunday = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 11, 1)
        )

        self.assertEqual(saturday, sunday)

    def test_holiday_shortened_week(self):
        daily = [
            candle("2026-11-23", 4000, 4050, 3980, 4020),
            candle("2026-11-24", 4020, 4100, 4000, 4080),
            candle("2026-11-25", 4080, 4120, 4050, 4100),
        ]

        result = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 11, 30)
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["datetime"], "2026-11-23")
        self.assertEqual(result[0]["daily_candles"], 3)
        self.assertEqual(result[0]["close"], 4100)

    def test_historical_weekly_cutoff(self):
        daily = [
            candle("2026-10-26", 4000, 4050, 3980, 4020),
            candle("2026-10-30", 4020, 4100, 4000, 4080),
            candle("2026-11-02", 4080, 4200, 4050, 4150),
        ]

        historical = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 11, 1)
        )

        extended = aggregate_ohlc(
            daily, "weekly", as_of=date(2026, 11, 3)
        )

        self.assertEqual(historical, extended[:1])
        self.assertEqual(len(historical), 1)


if __name__ == "__main__":
    unittest.main()
