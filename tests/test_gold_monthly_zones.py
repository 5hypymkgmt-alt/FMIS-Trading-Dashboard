"""Regression tests for Gold monthly structural zones."""

import unittest

from gold_monthly_zones import build_monthly_zones


def make_swing(swing_type="high", classification="major",
               status="confirmed", atr=200.0):
    return {
        "type": swing_type,
        "date": "2026-01-01",
        "price": 4000.0,
        "confirmed_at": "2026-03-01",
        "atr_at_confirmation": atr,
        "classification": classification,
        "structural_status": status,
    }


class GoldMonthlyZoneTests(unittest.TestCase):

    def test_major_high_creates_resistance(self):
        zones = build_monthly_zones([make_swing()])
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["type"], "resistance")

    def test_major_low_creates_support(self):
        zones = build_monthly_zones([
            make_swing(swing_type="low")
        ])
        self.assertEqual(zones[0]["type"], "support")

    def test_atr_zone_boundaries(self):
        zones = build_monthly_zones([make_swing()])
        self.assertEqual(zones[0]["level"], 4000.0)
        self.assertEqual(zones[0]["lower"], 3950.0)
        self.assertEqual(zones[0]["upper"], 4050.0)

    def test_minor_swing_excluded(self):
        zones = build_monthly_zones([
            make_swing(classification="minor")
        ])
        self.assertEqual(zones, [])

    def test_unconfirmed_swing_excluded(self):
        zones = build_monthly_zones([
            make_swing(status="unconfirmed")
        ])
        self.assertEqual(zones, [])

    def test_missing_atr_excluded(self):
        zones = build_monthly_zones([
            make_swing(atr=None)
        ])
        self.assertEqual(zones, [])

    def test_confirmation_date_preserved(self):
        zones = build_monthly_zones([make_swing()])
        self.assertEqual(
            zones[0]["confirmed_at"], "2026-03-01"
        )

    def test_invalid_atr_fraction_rejected(self):
        for fraction in (0, -0.1, 1.1):
            with self.subTest(fraction=fraction):
                with self.assertRaises(ValueError):
                    build_monthly_zones(
                        [make_swing()], atr_fraction=fraction
                    )


if __name__ == "__main__":
    unittest.main()


class GoldMonthlyZoneBreakTests(unittest.TestCase):

    def setUp(self):
        from gold_monthly_zones import track_monthly_zone_breaks
        self.track = track_monthly_zone_breaks
        self.resistance = build_monthly_zones([make_swing()])[0]
        self.support = build_monthly_zones([
            make_swing(swing_type="low")
        ])[0]

    def candle(self, day, close, high=None, low=None):
        return {
            "datetime": day,
            "open": close,
            "high": high if high is not None else close,
            "low": low if low is not None else close,
            "close": close,
        }

    def test_resistance_closing_break(self):
        candles = [self.candle("2026-04-01", 4100)]
        result = self.track(candles, [self.resistance])[0]
        self.assertEqual(result["status"], "broken")
        self.assertEqual(result["broken_at"], "2026-04-01")

    def test_support_closing_break(self):
        candles = [self.candle("2026-04-01", 3900)]
        result = self.track(candles, [self.support])[0]
        self.assertEqual(result["status"], "broken")

    def test_wick_without_closing_break(self):
        candles = [
            self.candle("2026-04-01", 4000, high=4200)
        ]
        result = self.track(candles, [self.resistance])[0]
        self.assertEqual(result["status"], "unbroken")

    def test_break_before_confirmation_ignored(self):
        candles = [
            self.candle("2026-02-01", 4200),
            self.candle("2026-03-01", 4200),
        ]
        result = self.track(candles, [self.resistance])[0]
        self.assertEqual(result["status"], "unbroken")

    def test_first_break_remains_stable(self):
        first = self.candle("2026-04-01", 4100)
        later = self.candle("2026-05-01", 4300)

        original = self.track([first], [self.resistance])[0]
        extended = self.track(
            [first, later], [self.resistance]
        )[0]

        self.assertEqual(
            original["broken_at"], extended["broken_at"]
        )
        self.assertEqual(
            original["break_close"], extended["break_close"]
        )


class GoldMonthlyCutoffTests(unittest.TestCase):

    def setUp(self):
        from gold_monthly_zones import (
            track_monthly_zone_breaks,
            is_completed_monthly_candle,
        )
        self.track = track_monthly_zone_breaks
        self.is_completed = is_completed_monthly_candle
        self.zone = build_monthly_zones([make_swing()])[0]

    def candle(self, month, close):
        return {
            "datetime": month,
            "open": close,
            "high": close,
            "low": close,
            "close": close,
        }

    def test_developing_month_excluded(self):
        candles = [self.candle("2026-11-01", 4200)]
        result = self.track(
            candles, [self.zone], as_of="2026-11-07"
        )[0]
        self.assertEqual(result["status"], "unbroken")
        self.assertIsNone(result["broken_at"])

    def test_completed_month_breaks_resistance(self):
        candles = [self.candle("2026-10-01", 4200)]
        result = self.track(
            candles, [self.zone], as_of="2026-11-07"
        )[0]
        self.assertEqual(result["status"], "broken")
        self.assertEqual(result["broken_at"], "2026-10-01")

    def test_break_confirmation_date(self):
        candles = [self.candle("2026-10-01", 4200)]
        result = self.track(
            candles, [self.zone], as_of="2026-11-07"
        )[0]
        self.assertEqual(
            result["break_confirmed_at"], "2026-11-01"
        )

    def test_month_completion_boundary(self):
        candle = self.candle("2026-10-01", 4200)
        self.assertFalse(
            self.is_completed(candle, "2026-10-31")
        )
        self.assertTrue(
            self.is_completed(candle, "2026-11-01")
        )

    def test_future_month_cannot_change_past(self):
        candles = [
            self.candle("2026-10-01", 4000),
            self.candle("2026-11-01", 4200),
        ]
        historical = self.track(
            candles, [self.zone], as_of="2026-11-07"
        )[0]
        future = self.track(
            candles, [self.zone], as_of="2026-12-01"
        )[0]

        self.assertEqual(historical["status"], "unbroken")
        self.assertEqual(future["status"], "broken")
        self.assertEqual(
            future["break_confirmed_at"], "2026-12-01"
        )
