"""Regression tests for FMIS Trade Confidence."""

import unittest

from trade_confidence import trade_confidence


class TradeConfidenceTests(unittest.TestCase):

    def setUp(self):
        self.market = {
            "price": {
                "status": "ok",
                "age_days": 0,
                "technical_score": 3,
                "adx14": 30,
                "market_regime": "Bullish Trend",
                "market_structure": {
                    "trend": "Bullish",
                    "choch": "None",
                },
                "factors": {
                    "price_vs_ema20": 1,
                    "ema20_vs_ema50": 1,
                    "weekly_trend": 1,
                    "momentum_5d": -1,
                    "rsi_14": 1,
                },
            }
        }

        self.data = {
            "macro": {
                "DFII10": {
                    "status": "ok",
                    "age_days": 1,
                    "direction": "falling",
                },
                "DTWEXBGS": {
                    "status": "ok",
                    "age_days": 1,
                    "direction": "falling",
                },
            }
        }

    def test_bullish_confidence_calculation(self):
        result = trade_confidence(
            "Gold", self.market, "Bullish", self.data
        )

        self.assertEqual(result["status"], "Complete")
        self.assertEqual(result["technical"], 24)
        self.assertEqual(result["trend"], 25)
        self.assertEqual(result["macro"], 25)
        self.assertEqual(result["structure"], 20)
        self.assertEqual(result["confidence"], 94)

    def test_confidence_remains_within_zero_and_one_hundred(self):
        for direction in ("Bullish", "Bearish"):
            result = trade_confidence(
                "Gold", self.market, direction, self.data
            )

            self.assertGreaterEqual(result["confidence"], 0)
            self.assertLessEqual(result["confidence"], 100)

    def test_missing_macro_data_returns_partial_data(self):
        result = trade_confidence(
            "Gold", self.market, "Bullish", {"macro": {}}
        )

        self.assertEqual(result["status"], "Partial Data")
        self.assertEqual(result["macro"], 0)

    def test_stale_price_returns_unavailable(self):
        self.market["price"]["age_days"] = 10

        result = trade_confidence(
            "Gold", self.market, "Bullish", self.data
        )

        self.assertEqual(result["status"], "Unavailable")

    def test_invalid_direction_is_rejected(self):
        with self.assertRaises(ValueError):
            trade_confidence(
                "Gold", self.market, "Neutral", self.data
            )


if __name__ == "__main__":
    unittest.main()
