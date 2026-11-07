"""Regression tests for Gold daily structural retests."""

import unittest
from datetime import date, timedelta

from gold_daily_retests import detect_daily_structural_retests


class GoldDailyRetestTests(unittest.TestCase):

    def test_bullish_retest_confirmation_and_invalidation(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "101",
                "high": "103",
                "low": "101.5",
                "close": "102",
            })

        # A bullish retest followed by a later invalidation.
        candles[29].update({
            "open": "101",
            "high": "102",
            "low": "99.8",
            "close": "101",
        })

        candles[32].update({
            "open": "101",
            "high": "101.5",
            "low": "98",
            "close": "99",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertEqual(result["resolved_date"], "2026-06-30")
        self.assertTrue(result["subsequently_invalidated"])
        self.assertEqual(result["invalidation_date"], "2026-07-03")


    def test_confirmation_remains_stable_after_invalidation(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "101",
                "high": "103",
                "low": "101.5",
                "close": "102",
            })

        candles[29].update({
            "open": "101",
            "high": "102",
            "low": "99.8",
            "close": "101",
        })

        candles[32].update({
            "open": "101",
            "high": "101.5",
            "low": "98",
            "close": "99",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        june_snapshot = [
            c for c in candles
            if c["datetime"] <= "2026-06-30"
        ]

        july_snapshot = [
            c for c in candles
            if c["datetime"] <= "2026-07-03"
        ]

        june = detect_daily_structural_retests(
            june_snapshot, bos
        )[0]

        july = detect_daily_structural_retests(
            july_snapshot, bos
        )[0]

        self.assertEqual(june["status"], "confirmed")
        self.assertFalse(june["subsequently_invalidated"])

        self.assertEqual(july["status"], "confirmed")
        self.assertTrue(july["subsequently_invalidated"])

        self.assertEqual(
            june["detected_date"], july["detected_date"]
        )
        self.assertEqual(
            june["resolved_date"], july["resolved_date"]
        )
        self.assertEqual(july["invalidation_date"], "2026-07-03")


    def test_bearish_retest_confirmation_and_invalidation(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "99",
                "high": "98.5",
                "low": "97",
                "close": "98",
            })

        candles[29].update({
            "open": "99",
            "high": "100.2",
            "low": "98",
            "close": "99",
        })

        candles[32].update({
            "open": "99",
            "high": "102",
            "low": "98.5",
            "close": "101",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bearish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["retest_type"], "exact_level")
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertEqual(result["resolved_date"], "2026-06-30")
        self.assertTrue(result["subsequently_invalidated"])
        self.assertEqual(result["invalidation_date"], "2026-07-03")


    def test_failed_bullish_retest(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "102",
                "high": "103",
                "low": "101.5",
                "close": "102",
            })

        candles[29].update({
            "open": "101",
            "high": "101.5",
            "low": "98",
            "close": "99",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["retest_type"], "exact_level")
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertEqual(result["resolved_date"], "2026-06-30")
        self.assertFalse(result["subsequently_invalidated"])


    def test_failed_bearish_retest(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "98",
                "high": "98.5",
                "low": "97",
                "close": "98",
            })

        candles[29].update({
            "open": "99",
            "high": "102",
            "low": "98.5",
            "close": "101",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bearish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["retest_type"], "exact_level")
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertEqual(result["resolved_date"], "2026-06-30")
        self.assertFalse(result["subsequently_invalidated"])


    def test_bullish_atr_zone_approach(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "102",
                "high": "103",
                "low": "101.5",
                "close": "102",
            })

        # Approaches the BOS level without touching it.
        candles[29].update({
            "open": "101",
            "high": "102",
            "low": "100.2",
            "close": "101",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["retest_type"], "zone_approach")
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertGreater(result["atr_at_retest"], 0)
        self.assertGreaterEqual(result["tolerance"], 0.2)


    def test_bearish_atr_zone_approach(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "98",
                "high": "98.5",
                "low": "97",
                "close": "98",
            })

        # Approaches resistance from below without touching it.
        candles[29].update({
            "open": "99",
            "high": "99.8",
            "low": "98",
            "close": "99",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bearish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["retest_type"], "zone_approach")
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertGreater(result["atr_at_retest"], 0)
        self.assertGreaterEqual(result["tolerance"], 0.2)


    def test_no_false_retest_outside_atr_tolerance(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "110",
                "high": "112",
                "low": "108",
                "close": "110",
            })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "awaiting_retest")
        self.assertIsNone(result["detected_date"])
        self.assertIsNone(result["retest_type"])
        self.assertIsNone(result["resolved_date"])


    def test_unresolved_retest_at_exact_level(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(30):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": "102",
                "high": "103",
                "low": "101.5",
                "close": "102",
            })

        candles[29].update({
            "open": "101",
            "high": "102",
            "low": "99.5",
            "close": "100",
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(result["status"], "detected")
        self.assertEqual(result["retest_type"], "exact_level")
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertIsNone(result["resolved_date"])
        self.assertFalse(result["subsequently_invalidated"])


    def _check_delayed_resolution(self, direction, next_close, expected):
        start = date(2026, 6, 1)
        candles = []

        for i in range(31):
            day = start + timedelta(days=i)
            if direction == "bullish":
                opening, high, low, close = 102, 103, 101.5, 102
            else:
                opening, high, low, close = 98, 98.5, 97, 98

            candles.append({
                "datetime": day.isoformat(),
                "open": str(opening),
                "high": str(high),
                "low": str(low),
                "close": str(close),
            })

        if direction == "bullish":
            candles[29].update({
                "open": "101", "high": "102",
                "low": "99.5", "close": "100",
            })
        else:
            candles[29].update({
                "open": "99", "high": "100.5",
                "low": "98", "close": "100",
            })

        candles[30].update({
            "open": "100",
            "high": str(max(102, next_close)),
            "low": str(min(98, next_close)),
            "close": str(next_close),
        })

        bos = [{
            "date": "2026-06-22",
            "direction": direction,
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(candles, bos)[0]

        self.assertEqual(result["status"], expected)
        self.assertEqual(result["detected_date"], "2026-06-30")
        self.assertEqual(result["resolved_date"], "2026-07-01")
        self.assertFalse(result["subsequently_invalidated"])

    def test_delayed_bullish_confirmation(self):
        self._check_delayed_resolution("bullish", 101, "confirmed")

    def test_delayed_bullish_failure(self):
        self._check_delayed_resolution("bullish", 99, "failed")

    def test_delayed_bearish_confirmation(self):
        self._check_delayed_resolution("bearish", 99, "confirmed")

    def test_delayed_bearish_failure(self):
        self._check_delayed_resolution("bearish", 101, "failed")


if __name__ == "__main__":
    unittest.main()


class GoldBOSTimingTests(unittest.TestCase):

    def test_retest_during_bos_week_is_ignored(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(35):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": 101,
                "high": 103,
                "low": 101.5,
                "close": 102,
            })

        # Qualifying retest during the BOS week: must be ignored.
        candles[23].update({
            "open": 101,
            "high": 102,
            "low": 99.8,
            "close": 101,
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        result = detect_daily_structural_retests(
            candles, bos
        )[0]

        self.assertEqual(
            result["first_eligible_date"], "2026-06-29"
        )
        self.assertEqual(result["status"], "awaiting_retest")
        self.assertIsNone(result["detected_date"])
        self.assertIsNone(result["resolved_date"])


class GoldDailyRetestHistoricalStabilityTests(unittest.TestCase):

    def test_confirmed_retest_stable_across_historical_snapshots(self):
        start = date(2026, 6, 1)
        candles = []

        for i in range(40):
            day = start + timedelta(days=i)
            candles.append({
                "datetime": day.isoformat(),
                "open": 102,
                "high": 103,
                "low": 101.5,
                "close": 102,
            })

        # First eligible retest: confirmed on 30 June.
        candles[29].update({
            "open": 101,
            "high": 102,
            "low": 99.8,
            "close": 101,
        })

        # Subsequent invalidation on 5 July.
        candles[34].update({
            "open": 101,
            "high": 102,
            "low": 98,
            "close": 99,
        })

        bos = [{
            "date": "2026-06-22",
            "direction": "bullish",
            "primary_level": 100,
        }]

        snapshots = {}

        for cutoff in (
            "2026-06-29",
            "2026-06-30",
            "2026-07-04",
            "2026-07-05",
            "2026-07-10",
        ):
            historical = [
                c for c in candles
                if c["datetime"] <= cutoff
            ]
            snapshots[cutoff] = detect_daily_structural_retests(
                historical, bos
            )[0]

        self.assertEqual(
            snapshots["2026-06-29"]["status"],
            "awaiting_retest",
        )

        for cutoff in (
            "2026-06-30",
            "2026-07-04",
            "2026-07-05",
            "2026-07-10",
        ):
            result = snapshots[cutoff]
            self.assertEqual(result["status"], "confirmed")
            self.assertEqual(result["detected_date"], "2026-06-30")
            self.assertEqual(result["resolved_date"], "2026-06-30")

        self.assertFalse(
            snapshots["2026-07-04"]["subsequently_invalidated"]
        )
        self.assertTrue(
            snapshots["2026-07-05"]["subsequently_invalidated"]
        )
        self.assertEqual(
            snapshots["2026-07-10"]["invalidation_date"],
            "2026-07-05",
        )
