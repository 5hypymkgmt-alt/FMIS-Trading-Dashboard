"""Regression tests for Gold weekly market structure."""

import unittest
from datetime import date, timedelta

from gold_market_structure import (
    detect_confirmed_swings,
    calculate_atr,
    calculate_atr_series,
    classify_structural_swings,
    label_primary_structure,
    detect_structural_breaks,
    consolidate_structural_breaks,
    classify_weekly_market_bias,
    detect_structural_retests,
)


def make_candles(count=40):
    start = date(2026, 1, 1)
    candles = []

    for i in range(count):
        day = start + timedelta(days=i)
        candles.append({
            "datetime": day.isoformat(),
            "open": 100,
            "high": 102,
            "low": 98,
            "close": 100,
        })

    return candles


class GoldSwingDetectionTests(unittest.TestCase):

    def test_strength_two_confirms_swing_high(self):
        candles = make_candles(7)

        candles[3]["high"] = 110

        swings = detect_confirmed_swings(
            candles, strength=2
        )

        highs = [s for s in swings if s["type"] == "high"]

        self.assertEqual(len(highs), 1)
        self.assertEqual(highs[0]["date"], candles[3]["datetime"])
        self.assertEqual(highs[0]["confirmed_at"], candles[5]["datetime"])

    def test_strength_two_confirms_swing_low(self):
        candles = make_candles(7)

        candles[3]["low"] = 90

        swings = detect_confirmed_swings(
            candles, strength=2
        )

        lows = [s for s in swings if s["type"] == "low"]

        self.assertEqual(len(lows), 1)
        self.assertEqual(lows[0]["date"], candles[3]["datetime"])
        self.assertEqual(lows[0]["confirmed_at"], candles[5]["datetime"])

    def test_unconfirmed_latest_swings_are_excluded(self):
        candles = make_candles(5)
        candles[4]["high"] = 120

        swings = detect_confirmed_swings(
            candles, strength=2
        )

        self.assertEqual(swings, [])

    def test_equal_highs_do_not_create_swing(self):
        candles = make_candles(7)

        candles[2]["high"] = 110
        candles[3]["high"] = 110

        swings = detect_confirmed_swings(
            candles, strength=2
        )

        self.assertFalse(
            any(s["type"] == "high" for s in swings)
        )

    def test_invalid_strength_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_confirmed_swings(
                make_candles(), strength=0
            )


class GoldATRTests(unittest.TestCase):

    def test_atr_calculation(self):
        candles = make_candles(4)

        candles[1].update(high=104, low=98, close=102)
        candles[2].update(high=105, low=100, close=103)
        candles[3].update(high=106, low=101, close=104)

        result = calculate_atr(candles, period=2)

        # True ranges: 6, 5, 5
        # Initial ATR: 5.5
        # Wilder-smoothed ATR: 5.25
        self.assertAlmostEqual(result, 5.25)

    def test_atr_series_alignment(self):
        candles = make_candles(5)

        result = calculate_atr_series(
            candles, period=2
        )

        self.assertEqual(len(result), 5)
        self.assertIsNone(result[0]["atr"])
        self.assertIsNone(result[1]["atr"])
        self.assertIsNotNone(result[2]["atr"])

    def test_insufficient_atr_history_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_atr(
                make_candles(2), period=2
            )


if __name__ == "__main__":
    unittest.main()


class GoldStructuralClassificationTests(unittest.TestCase):

    def test_major_swing_at_two_atr(self):
        candles = make_candles(50)

        # Establish an initial low.
        candles[20]["low"] = 90

        # Confirmed high, 20 points above the low.
        candles[25]["high"] = 110

        classified = classify_structural_swings(
            candles,
            strength=2,
            atr_period=14,
            major_threshold=2.0,
        )

        high = next(
            s for s in classified
            if s["type"] == "high"
            and s["date"] == candles[25]["datetime"]
        )

        self.assertEqual(high["classification"], "major")
        self.assertGreaterEqual(high["distance_atr"], 2.0)

    def test_minor_swing_below_two_atr(self):
        candles = make_candles(40)

        for candle in candles:
            candle["high"] = 102
            candle["low"] = 98

        candles[18].update(high=101, low=97)
        candles[25].update(high=104, low=99)

        classified = classify_structural_swings(
            candles,
            strength=2,
            atr_period=14,
            major_threshold=2.0,
        )

        high = next(
            s for s in classified
            if s["type"] == "high"
            and s["date"] == candles[25]["datetime"]
        )

        self.assertEqual(high["classification"], "minor")
        self.assertLess(high["distance_atr"], 2.0)

    def test_first_swing_without_opposite_is_unclassified(self):
        candles = make_candles(40)
        candles[20]["high"] = 110

        classified = classify_structural_swings(
            candles,
            strength=2,
            atr_period=14,
        )

        high = next(
            s for s in classified
            if s["type"] == "high"
            and s["date"] == candles[20]["datetime"]
        )

        self.assertEqual(high["classification"], "unclassified")
        self.assertEqual(high["structural_status"], "confirmed")

    def test_invalid_major_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_structural_swings(
                make_candles(),
                major_threshold=0,
            )


class GoldHistoricalClassificationTests(unittest.TestCase):

    def test_confirmed_swing_classification_stays_stable(self):
        candles = make_candles(50)

        candles[18].update(high=101, low=97)
        candles[25].update(high=110, low=99)

        snapshots = {}

        for cutoff in (30, 35, 40, 45, 50):
            snapshots[cutoff] = classify_structural_swings(
                candles[:cutoff],
                strength=2,
                atr_period=14,
                major_threshold=2.0,
            )

        target_date = candles[25]["datetime"]
        results = []

        for cutoff, swings in snapshots.items():
            high = next(
                (
                    s for s in swings
                    if s["type"] == "high"
                    and s["date"] == target_date
                ),
                None,
            )

            self.assertIsNotNone(high)

            results.append(high)

        first = results[0]

        for later in results[1:]:
            self.assertEqual(later["confirmed_at"], first["confirmed_at"])
            self.assertEqual(later["classification"], first["classification"])
            self.assertEqual(later["distance_atr"], first["distance_atr"])


class GoldBOSTests(unittest.TestCase):

    def setUp(self):
        self.swings = [
            {
                "type": "high",
                "date": "2026-01-10",
                "confirmed_at": "2026-01-20",
                "price": 110.0,
                "classification": "major",
                "structural_status": "confirmed",
            },
            {
                "type": "low",
                "date": "2026-01-15",
                "confirmed_at": "2026-01-25",
                "price": 90.0,
                "classification": "major",
                "structural_status": "confirmed",
            },
        ]

    def test_bullish_weekly_close_breaks_major_high(self):
        candles = [
            {"datetime": "2026-01-26", "close": 109},
            {"datetime": "2026-02-02", "close": 111},
        ]

        events = detect_structural_breaks(candles, self.swings)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["direction"], "bullish")
        self.assertEqual(events[0]["level_price"], 110)

    def test_bearish_weekly_close_breaks_major_low(self):
        candles = [
            {"datetime": "2026-01-26", "close": 91},
            {"datetime": "2026-02-02", "close": 89},
        ]

        events = detect_structural_breaks(candles, self.swings)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["direction"], "bearish")
        self.assertEqual(events[0]["level_price"], 90)

    def test_break_before_swing_confirmation_is_ignored(self):
        candles = [
            {"datetime": "2026-01-19", "close": 115},
            {"datetime": "2026-01-26", "close": 109},
        ]

        events = detect_structural_breaks(candles, self.swings)

        self.assertEqual(events, [])

    def test_intraperiod_high_without_closing_break_is_ignored(self):
        candles = [
            {
                "datetime": "2026-01-26",
                "open": 109,
                "high": 115,
                "low": 108,
                "close": 109,
            }
        ]

        events = detect_structural_breaks(candles, self.swings)

        self.assertEqual(events, [])

    def test_same_level_is_only_broken_once(self):
        candles = [
            {"datetime": "2026-01-26", "close": 111},
            {"datetime": "2026-02-02", "close": 112},
            {"datetime": "2026-02-09", "close": 113},
        ]

        events = detect_structural_breaks(candles, self.swings)

        bullish = [
            event for event in events
            if event["direction"] == "bullish"
        ]

        self.assertEqual(len(bullish), 1)

    def test_minor_swings_cannot_generate_bos(self):
        minor_swings = [
            {
                **self.swings[0],
                "classification": "minor",
            }
        ]

        candles = [
            {"datetime": "2026-01-26", "close": 115}
        ]

        events = detect_structural_breaks(candles, minor_swings)

        self.assertEqual(events, [])


class GoldBOSConsolidationTests(unittest.TestCase):

    def setUp(self):
        self.swings = [
            {
                "type": "high",
                "date": "2026-01-05",
                "confirmed_at": "2026-01-15",
                "price": 110.0,
                "classification": "major",
                "structural_status": "confirmed",
            },
            {
                "type": "high",
                "date": "2026-01-12",
                "confirmed_at": "2026-01-22",
                "price": 115.0,
                "classification": "major",
                "structural_status": "confirmed",
            },
            {
                "type": "low",
                "date": "2026-01-08",
                "confirmed_at": "2026-01-18",
                "price": 90.0,
                "classification": "major",
                "structural_status": "confirmed",
            },
        ]

    def test_multiple_bullish_breaks_consolidate(self):
        events = [
            {
                "date": "2026-02-02",
                "direction": "bullish",
                "level_date": "2026-01-05",
                "level_price": 110.0,
                "close": 118.0,
            },
            {
                "date": "2026-02-02",
                "direction": "bullish",
                "level_date": "2026-01-12",
                "level_price": 115.0,
                "close": 118.0,
            },
        ]

        signals = consolidate_structural_breaks(
            events, self.swings
        )

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["direction"], "bullish")
        self.assertEqual(signals[0]["levels_broken"], 2)
        self.assertEqual(signals[0]["broken_levels"], [110.0, 115.0])

    def test_latest_confirmed_level_becomes_primary(self):
        events = [
            {
                "date": "2026-02-02",
                "direction": "bullish",
                "level_date": "2026-01-05",
                "level_price": 110.0,
                "close": 118.0,
            },
            {
                "date": "2026-02-02",
                "direction": "bullish",
                "level_date": "2026-01-12",
                "level_price": 115.0,
                "close": 118.0,
            },
        ]

        signals = consolidate_structural_breaks(
            events, self.swings
        )

        self.assertEqual(signals[0]["primary_level"], 115.0)
        self.assertEqual(
            signals[0]["primary_level_date"], "2026-01-12"
        )

    def test_opposite_directions_remain_separate(self):
        events = [
            {
                "date": "2026-02-02",
                "direction": "bullish",
                "level_date": "2026-01-05",
                "level_price": 110.0,
                "close": 118.0,
            },
            {
                "date": "2026-02-02",
                "direction": "bearish",
                "level_date": "2026-01-08",
                "level_price": 90.0,
                "close": 85.0,
            },
        ]

        signals = consolidate_structural_breaks(
            events, self.swings
        )

        self.assertEqual(len(signals), 2)
        self.assertEqual(
            {s["direction"] for s in signals},
            {"bullish", "bearish"},
        )


class GoldWeeklyMarketBiasTests(unittest.TestCase):

    def make_swings(self, highs, lows):
        swings = []

        for i, price in enumerate(highs):
            swings.append({
                "type": "high",
                "price": price,
            })

        for i, price in enumerate(lows):
            swings.append({
                "type": "low",
                "price": price,
            })

        return swings

    def test_bullish_structure_and_bos(self):
        swings = self.make_swings(
            [100, 110],
            [80, 90],
        )
        bos = [{"direction": "bullish", "date": "2026-06-01"}]

        result = classify_weekly_market_bias(swings, bos)

        self.assertEqual(result["bias"], "Bullish")

    def test_bearish_structure_and_bos(self):
        swings = self.make_swings(
            [110, 100],
            [90, 80],
        )
        bos = [{"direction": "bearish", "date": "2026-06-01"}]

        result = classify_weekly_market_bias(swings, bos)

        self.assertEqual(result["bias"], "Bearish")

    def test_conflicting_bullish_structure_and_bearish_bos(self):
        swings = self.make_swings(
            [100, 110],
            [80, 90],
        )
        bos = [{"direction": "bearish", "date": "2026-06-01"}]

        result = classify_weekly_market_bias(swings, bos)

        self.assertEqual(result["bias"], "Neutral")

    def test_conflicting_bearish_structure_and_bullish_bos(self):
        swings = self.make_swings(
            [110, 100],
            [90, 80],
        )
        bos = [{"direction": "bullish", "date": "2026-06-01"}]

        result = classify_weekly_market_bias(swings, bos)

        self.assertEqual(result["bias"], "Neutral")

    def test_insufficient_structure_returns_neutral(self):
        swings = self.make_swings(
            [100],
            [80],
        )
        bos = [{"direction": "bullish", "date": "2026-06-01"}]

        result = classify_weekly_market_bias(swings, bos)

        self.assertEqual(result["bias"], "Neutral")


class GoldWeeklyRetestTests(unittest.TestCase):

    def make_candles(self, direction, outcome="confirmed"):
        start = date(2026, 6, 1)
        candles = []

        for i in range(18):
            day = start + timedelta(days=i)

            if direction == "bullish":
                candle = {
                    "datetime": day.isoformat(),
                    "open": 102, "high": 103,
                    "low": 101, "close": 102,
                }
            else:
                candle = {
                    "datetime": day.isoformat(),
                    "open": 98, "high": 99,
                    "low": 97, "close": 98,
                }

            candles.append(candle)

        if direction == "bullish":
            candles[15].update({
                "open": 101, "high": 102,
                "low": 99.8,
                "close": 99 if outcome == "failed" else 101,
            })

            if outcome == "invalidated":
                candles[17].update({
                    "open": 101, "high": 102,
                    "low": 98, "close": 99,
                })
        else:
            candles[15].update({
                "open": 99, "high": 100.2,
                "low": 98,
                "close": 101 if outcome == "failed" else 99,
            })

            if outcome == "invalidated":
                candles[17].update({
                    "open": 99, "high": 102,
                    "low": 98.5, "close": 101,
                })

        return candles

    def make_bos(self, direction):
        return [{
            "date": "2026-06-15",
            "direction": direction,
            "primary_level": 100,
            "primary_level_date": "2026-06-01",
        }]

    def test_bullish_retest_confirmation(self):
        result = detect_structural_retests(
            self.make_candles("bullish"),
            self.make_bos("bullish"),
        )[0]

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["resolved_date"], "2026-06-16")

    def test_bearish_retest_confirmation(self):
        result = detect_structural_retests(
            self.make_candles("bearish"),
            self.make_bos("bearish"),
        )[0]

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["resolved_date"], "2026-06-16")

    def test_failed_weekly_retest(self):
        for direction in ("bullish", "bearish"):
            with self.subTest(direction=direction):
                result = detect_structural_retests(
                    self.make_candles(direction, "failed"),
                    self.make_bos(direction),
                )[0]

                self.assertEqual(result["status"], "failed")

    def test_confirmed_weekly_retest_invalidation(self):
        for direction in ("bullish", "bearish"):
            with self.subTest(direction=direction):
                result = detect_structural_retests(
                    self.make_candles(direction, "invalidated"),
                    self.make_bos(direction),
                )[0]

                self.assertEqual(result["status"], "confirmed")
                self.assertEqual(
                    result["resolved_date"], "2026-06-16"
                )
                self.assertTrue(
                    result["subsequently_invalidated"]
                )
                self.assertEqual(
                    result["invalidation_date"], "2026-06-18"
                )
