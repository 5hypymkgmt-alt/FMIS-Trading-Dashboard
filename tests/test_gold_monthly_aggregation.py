"""Regression tests for completed Gold monthly candles."""

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


class GoldMonthlyAggregationTests(unittest.TestCase):

    def test_monthly_ohlc_aggregation(self):
        daily = [
            candle("2026-10-01", 4000, 4050, 3980, 4020),
            candle("2026-10-15", 4020, 4100, 4000, 4080),
            candle("2026-10-30", 4080, 4120, 4050, 4100),
        ]

        result = aggregate_ohlc(
            daily, "monthly", as_of=date.fromisoformat("2026-11-01")
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["open"], 4000)
        self.assertEqual(result[0]["high"], 4120)
        self.assertEqual(result[0]["low"], 3980)
        self.assertEqual(result[0]["close"], 4100)

    def test_developing_month_excluded(self):
        daily = [
            candle("2026-10-30", 4000, 4100, 3950, 4050),
            candle("2026-11-06", 4050, 4300, 4000, 4250),
        ]

        result = aggregate_ohlc(
            daily, "monthly", as_of=date.fromisoformat("2026-11-07")
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["datetime"], "2026-10-01")

    def test_month_becomes_available_next_month(self):
        daily = [
            candle("2026-10-30", 4000, 4100, 3950, 4050),
        ]

        october = aggregate_ohlc(
            daily, "monthly", as_of=date.fromisoformat("2026-10-31")
        )
        november = aggregate_ohlc(
            daily, "monthly", as_of=date.fromisoformat("2026-11-01")
        )

        self.assertEqual(october, [])
        self.assertEqual(len(november), 1)

    def test_december_year_boundary(self):
        daily = [
            candle("2025-12-31", 4000, 4100, 3950, 4050),
            candle("2026-01-02", 4050, 4200, 4000, 4150),
        ]

        result = aggregate_ohlc(
            daily, "monthly", as_of=date.fromisoformat("2026-01-03")
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["datetime"], "2025-12-01")


if __name__ == "__main__":
    unittest.main()
