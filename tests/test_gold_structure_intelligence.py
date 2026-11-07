"""Tests for unified Gold Market Structure Intelligence."""

import unittest
from unittest.mock import patch
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


    def test_daily_retest_outcomes_never_reverse_weekly_bias(self):

        expected_bias = {
            "bias": "Bullish",
            "latest_bos": "2025-01-01",
        }

        daily_outcomes = [
            {
                "status": "confirmed",
                "subsequently_invalidated": False,
            },
            {
                "status": "failed",
                "subsequently_invalidated": False,
            },
            {
                "status": "confirmed",
                "subsequently_invalidated": True,
            },
        ]

        with patch(
            "gold_structure_intelligence.classify_weekly_market_bias",
            return_value=expected_bias,
        ):

            for outcome in daily_outcomes:

                with self.subTest(outcome=outcome):

                    with patch(
                        "gold_structure_intelligence.detect_daily_structural_retests",
                        return_value=[outcome],
                    ):

                        result = build_gold_structure_intelligence(
                            self.daily,
                            as_of="2026-03-01",
                        )

                    self.assertEqual(
                        result["weekly"]["bias"],
                        expected_bias,
                    )



if __name__ == "__main__":
    unittest.main()
