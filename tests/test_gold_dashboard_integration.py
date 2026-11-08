"""Isolated tests for FMIS Gold dashboard integration."""

import unittest
from unittest.mock import patch

from update import update_gold_structure


class TestGoldDashboardIntegration(unittest.TestCase):

    def setUp(self):
        self.out = {"markets": {"Gold": {"symbol": "XAU/USD"}}}

    @patch("update.fetch_gold_structure")
    def test_successful_update(self, fetch):
        fetch.return_value = {
            "status": "ok",
            "market": "XAU/USD",
            "weekly": {"bias": {"bias": "Bullish"}},
        }

        update_gold_structure(self.out, {})

        result = self.out["markets"]["Gold"]["market_structure"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["weekly"]["bias"]["bias"], "Bullish")
        fetch.assert_called_once()

    @patch("update.fetch_gold_structure")
    def test_stale_fallback(self, fetch):
        fetch.side_effect = RuntimeError("API unavailable")
        previous = {
            "markets": {
                "Gold": {
                    "market_structure": {
                        "status": "ok",
                        "weekly": {"bias": {"bias": "Bearish"}},
                    }
                }
            }
        }

        update_gold_structure(self.out, previous)

        result = self.out["markets"]["Gold"]["market_structure"]
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["weekly"]["bias"]["bias"], "Bearish")
        self.assertIn("API unavailable", result["fallback_reason"])
        self.assertEqual(
            previous["markets"]["Gold"]["market_structure"]["status"],
            "ok",
        )

    @patch("update.fetch_gold_structure")
    def test_unavailable_without_previous_data(self, fetch):
        fetch.side_effect = RuntimeError("API unavailable")

        update_gold_structure(self.out, {})

        result = self.out["markets"]["Gold"]["market_structure"]
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("API unavailable", result["reason"])

    @patch("update.fetch_gold_structure")
    def test_other_markets_unchanged(self, fetch):
        out = {"markets": {"S&P 500": {"symbol": "SPY"}}}

        update_gold_structure(out, {})

        fetch.assert_not_called()
        self.assertNotIn("Gold", out["markets"])


if __name__ == "__main__":
    unittest.main()
