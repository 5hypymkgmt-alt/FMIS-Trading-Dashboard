"""Tests for unified Gold Market Structure Intelligence."""

import unittest
from datetime import date, timedelta

from gold_structure_intelligence import build_gold_structure_intelligence


class TestGoldStructureIntelligence(unittest.TestCase):

    def setUp(self):
        start = date(2024, 1, 1)
        self.daily = [
            {
                "datetime": (start + timedelta(days=i)).isoformat(),
                "open": 2000.0,
                "high": 2010.0,
                "low": 1990.0,
                "close": 2000.0,
            }
            for i in range(800)
        ]

    def test_unified_output(self):
        result = build_gold_structure_intelligence(
            self.daily, as_of="2026-03-01"
        )

        self.assertEqual(result["market"], "XAU/USD")
        self.assertEqual(result["weekly"]["bias"]["bias"], "Neutral")
        self.assertEqual(result["weekly"]["bos_count"], 0)
        self.assertEqual(result["daily"]["retest_count"], 0)
        self.assertEqual(len(result["monthly"]["zones"]), 0)

    def test_future_candles_excluded(self):
        cutoff = "2025-06-01"

        original = build_gold_structure_intelligence(
            self.daily, as_of=cutoff
        )

        future = {
            "datetime": "2026-12-01",
            "open": 5000.0,
            "high": 6000.0,
            "low": 4000.0,
            "close": 5500.0,
        }

        replay = build_gold_structure_intelligence(
            self.daily + [future], as_of=cutoff
        )

        self.assertEqual(original, replay)

    def test_historical_cutoff_stability(self):
        cutoff = "2025-09-01"

        full = build_gold_structure_intelligence(
            self.daily, as_of=cutoff
        )

        truncated = [
            candle for candle in self.daily
            if candle["datetime"] < cutoff
        ]

        replay = build_gold_structure_intelligence(
            truncated, as_of=cutoff
        )

        self.assertEqual(full, replay)


if __name__ == "__main__":
    unittest.main()
