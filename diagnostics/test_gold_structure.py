"""Validate Gold market structure using historical XAU/USD data."""

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gold_market_structure import (
    aggregate_ohlc,
    detect_confirmed_swings,
    classify_structural_swings,
    label_primary_structure,
    detect_structural_breaks,
    consolidate_structural_breaks,
    select_alternating_major_swings,
    classify_weekly_market_bias,
)

from gold_daily_retests import detect_daily_structural_retests

from gold_monthly_zones import (
    build_monthly_zones,
    track_monthly_zone_breaks,
)

API = "https://api.twelvedata.com/time_series"
KEY = os.environ.get("PRICE_API_KEY")

if not KEY:
    raise RuntimeError("PRICE_API_KEY is missing")

params = {
    "symbol": "XAU/USD",
    "interval": "1day",
    "outputsize": 1000,
    "timezone": "UTC",
    "apikey": KEY,
    "format": "JSON",
}

response = requests.get(API, params=params, timeout=30)
response.raise_for_status()
data = response.json()

daily = data.get("values", [])

if not daily:
    raise RuntimeError(
        data.get("message", "No historical Gold candles returned")
    )

# Validate historical candle integrity before aggregation.
from datetime import date
from math import isfinite

seen_dates = set()

for candle in daily:
    candle_date = date.fromisoformat(str(candle["datetime"])[:10])

    if candle_date in seen_dates:
        raise ValueError(f"Duplicate Gold candle date: {candle_date}")

    seen_dates.add(candle_date)

    o, h, l, c = (
        float(candle[field])
        for field in ("open", "high", "low", "close")
    )

    if not all(isfinite(value) and value > 0 for value in (o, h, l, c)):
        raise ValueError(f"Invalid Gold OHLC prices: {candle_date}")

    if h < max(o, c, l) or l > min(o, c, h):
        raise ValueError(f"Inconsistent Gold OHLC: {candle_date}")

# Exclude today's potentially unfinished daily candle.
from datetime import datetime, timezone

utc_today = datetime.now(timezone.utc).date()

daily = [
    candle for candle in daily
    if date.fromisoformat(str(candle["datetime"])[:10]) < utc_today
]

if not daily:
    raise RuntimeError("No completed Gold daily candles available")

print("PASS: Unfinished daily candles excluded")

daily.sort(key=lambda candle: candle["datetime"])

print("PASS: Historical Gold candle integrity validated")

weekly = aggregate_ohlc(daily, "weekly")
monthly = aggregate_ohlc(daily, "monthly")

print("FMIS GOLD MARKET STRUCTURE DIAGNOSTIC")
print("Daily candles retrieved:", len(daily))
print("Completed weekly candles:", len(weekly))
print("Completed monthly candles:", len(monthly))
print("Latest completed week:", weekly[-1]["datetime"] if weekly else "None")
print("Latest completed month:", monthly[-1]["datetime"] if monthly else "None")


weekly_swings = detect_confirmed_swings(weekly, strength=2)
monthly_swings = detect_confirmed_swings(monthly, strength=2)

print("\nCONFIRMED STRUCTURAL SWINGS")
print("Weekly confirmed swings:", len(weekly_swings))
print("Monthly confirmed swings:", len(monthly_swings))

print("\nLATEST WEEKLY SWINGS")
for swing in weekly_swings[-5:]:
    print(swing)

print("\nLATEST MONTHLY SWINGS")
for swing in monthly_swings[-5:]:
    print(swing)


print("\nATR-BASED STRUCTURAL CLASSIFICATION")

for timeframe, candles in (
    ("WEEKLY", weekly),
    ("MONTHLY", monthly),
):
    classified = classify_structural_swings(
        candles,
        strength=2,
        atr_period=14,
        major_threshold=2.0,
    )

    print(f"\n{timeframe} STRUCTURE")
    print("Major swings:", sum(
        s["classification"] == "major" for s in classified
    ))
    print("Minor swings:", sum(
        s["classification"] == "minor" for s in classified
    ))
    print("Unclassified swings:", sum(
        s["classification"] == "unclassified" for s in classified
    ))
    print("Ambiguous swings:", sum(
        s["classification"] == "ambiguous" for s in classified
    ))

    print("Latest classified swings:")
    for swing in classified[-5:]:
        print(swing)

    labelled = label_primary_structure(classified)

    print(f"\n{timeframe} PRIMARY STRUCTURE LABELS")
    major_labelled = [
        swing for swing in labelled
        if swing["classification"] == "major"
    ]

    for swing in major_labelled[-10:]:
        print(
            swing["date"],
            swing["type"],
            round(swing["price"], 2),
            swing["structure_label"] or "INITIAL",
            "confirmed:", swing["confirmed_at"],
        )

# Historical weekly Break of Structure (BOS) analysis.
weekly_classified = classify_structural_swings(
    weekly,
    strength=2,
    atr_period=14,
    major_threshold=2.0,
)

weekly_break_events = detect_structural_breaks(
    weekly, weekly_classified
)

weekly_bos = consolidate_structural_breaks(
    weekly_break_events, weekly_classified
)

full_alternating_swings = select_alternating_major_swings(
    weekly_classified
)

full_weekly_bias = classify_weekly_market_bias(
    full_alternating_swings,
    weekly_bos,
)

print("\nFULL-HISTORY WEEKLY MARKET BIAS")
print("Bias:", full_weekly_bias["bias"])
print("Latest BOS:", full_weekly_bias.get("latest_bos"))
print("Latest BOS date:", full_weekly_bias.get("latest_bos_date"))

print("\nWEEKLY BREAK OF STRUCTURE (BOS)")
print("Individual structural breaks:", len(weekly_break_events))
print("Consolidated weekly BOS signals:", len(weekly_bos))

for bos in weekly_bos[-10:]:
    print(
        bos["date"],
        bos["direction"].upper(),
        "Level:", round(bos["primary_level"], 2),
        "Close:", round(bos["close"], 2),
        "Levels broken:", bos["levels_broken"],
    )

# Historical non-repainting validation for weekly BOS signals.
print("\nWEEKLY BOS HISTORICAL STABILITY TEST")

full_signals = {
    (b["date"], b["direction"]): b
    for b in weekly_bos
}

cutoffs = [len(weekly) // 2, len(weekly) * 3 // 4, len(weekly) - 5]

for cutoff in cutoffs:
    historical_weekly = weekly[:cutoff]

    historical_swings = classify_structural_swings(
        historical_weekly,
        strength=2,
        atr_period=14,
        major_threshold=2.0,
    )

    historical_events = detect_structural_breaks(
        historical_weekly, historical_swings
    )

    historical_bos = consolidate_structural_breaks(
        historical_events, historical_swings
    )

    if not historical_weekly:
        raise AssertionError("No historical weekly candles")

    latest_week = historical_weekly[-1]["datetime"]

    # Reconstruct bias using only information available at this cutoff.
    reconstructed_bias = classify_weekly_market_bias(
        select_alternating_major_swings(historical_swings),
        historical_bos,
    )

    # Independently filter the full-history results to the same cutoff.
    available_full_swings = [
        s for s in weekly_classified
        if s["confirmed_at"] <= latest_week
    ]

    available_full_bos = [
        b for b in weekly_bos
        if b["date"] <= latest_week
    ]

    expected_bias = classify_weekly_market_bias(
        select_alternating_major_swings(available_full_swings),
        available_full_bos,
    )

    assert reconstructed_bias == expected_bias, (
        f"Historical weekly bias mismatch at {latest_week}: "
        f"reconstructed={reconstructed_bias}, "
        f"expected={expected_bias}"
    )

    print(
        "PASS: Weekly bias stable at",
        latest_week,
        "| Bias:",
        reconstructed_bias["bias"],
    )

    expected_keys = {
        (b["date"], b["direction"])
        for b in weekly_bos
        if b["date"] <= latest_week
    }

    reconstructed_keys = {
        (b["date"], b["direction"])
        for b in historical_bos
    }

    assert reconstructed_keys == expected_keys, (
        f"Historical BOS mismatch at {latest_week}: "
        f"missing={expected_keys - reconstructed_keys}, "
        f"unexpected={reconstructed_keys - expected_keys}"
    )

    for signal in historical_bos:
        key = (signal["date"], signal["direction"])
        assert key in full_signals, (
            f"Historical BOS disappeared: {key}"
        )

        original = full_signals[key]

        for field in (
            "primary_level",
            "primary_level_date",
            "close",
            "levels_broken",
            "broken_levels",
        ):
            assert signal[field] == original[field], (
                f"Historical BOS changed: {key}, field={field}"
            )

    print(
        "PASS:",
        cutoff,
        "weekly candles,",
        len(historical_bos),
        "BOS signals stable",
    )

print("PASS: Historical weekly BOS stability validation")

# Historical daily retests following confirmed weekly BOS signals.
print("\nGOLD WEEKLY BOS → DAILY RETEST ANALYSIS")

daily_retests = detect_daily_structural_retests(
    daily,
    weekly_bos,
    atr_period=14,
    tolerance_atr=0.25,
)

print("Weekly BOS signals analysed:", len(weekly_bos))
print("Daily retest records:", len(daily_retests))

for status in ("awaiting_retest", "detected", "confirmed", "failed"):
    count = sum(r["status"] == status for r in daily_retests)
    print(status.upper() + ":", count)

print("\nLATEST DAILY RETEST RESULTS")

for retest in daily_retests[-10:]:
    print(
        "BOS:", retest["bos_date"],
        "| Direction:", retest["direction"].upper(),
        "| Level:", round(retest["level"], 2),
        "| Status:", retest["status"].upper(),
        "| Detected:", retest["detected_date"],
        "| Resolved:", retest["resolved_date"],
        "| Invalidated:", retest["subsequently_invalidated"],
    )

# Historical snapshot stability for Gold daily structural retests.
from datetime import timedelta
print("\nGOLD DAILY RETEST HISTORICAL STABILITY TEST")

full_retests = {
    (r["bos_date"], r["direction"], r["level"]): r
    for r in daily_retests
}

daily_cutoffs = [
    len(daily) // 2,
    len(daily) * 3 // 4,
    len(daily) - 5,
]

for cutoff in daily_cutoffs:
    historical_daily = daily[:cutoff]
    last_date = historical_daily[-1]["datetime"]

    # Only use weekly BOS signals already confirmed by this date.
    historical_bos = [
        b for b in weekly_bos
        if (
            date.fromisoformat(b["date"])
            + timedelta(days=7)
        ).isoformat() <= last_date
    ]

    historical_retests = detect_daily_structural_retests(
        historical_daily,
        historical_bos,
        atr_period=14,
        tolerance_atr=0.25,
    )

    for earlier in historical_retests:
        key = (
            earlier["bos_date"],
            earlier["direction"],
            earlier["level"],
        )
        assert key in full_retests, (
            f"Historical retest disappeared: {key}"
        )

        later = full_retests[key]

        if earlier["detected_date"] is not None:
            assert earlier["detected_date"] == later["detected_date"], (
                f"Retest detection date changed: {key}"
            )
            assert earlier["retest_type"] == later["retest_type"], (
                f"Retest type changed: {key}"
            )

        if earlier["resolved_date"] is not None:
            assert earlier["resolved_date"] == later["resolved_date"], (
                f"Retest resolution date changed: {key}"
            )
            assert earlier["status"] == later["status"], (
                f"Retest resolution status changed: {key}"
            )

        if earlier["subsequently_invalidated"]:
            assert later["subsequently_invalidated"], (
                f"Historical invalidation disappeared: {key}"
            )
            assert earlier["invalidation_date"] == later["invalidation_date"], (
                f"Historical invalidation date changed: {key}"
            )

    print(
        "PASS:",
        cutoff,
        "daily candles,",
        len(historical_retests),
        "historical retests stable",
    )

print("PASS: Historical Gold daily retest stability validation")

# End-to-end historical replay using only data available at each cutoff.
print("\nGOLD END-TO-END HISTORICAL REPLAY TEST")

for cutoff in daily_cutoffs:
    historical_daily = daily[:cutoff]
    snapshot_date = date.fromisoformat(historical_daily[-1]["datetime"])
    if snapshot_date.weekday() == 4:
        # Friday close: the trading week is complete.
        as_of = snapshot_date + timedelta(days=3)
    else:
        # Monday-Thursday: exclude the unfinished current week.
        as_of = snapshot_date - timedelta(
            days=snapshot_date.weekday()
        )

    snapshot_weekly = aggregate_ohlc(
        historical_daily, "weekly", as_of=as_of
    )

    snapshot_swings = classify_structural_swings(
        snapshot_weekly,
        strength=2,
        atr_period=14,
        major_threshold=2.0,
    )

    snapshot_breaks = detect_structural_breaks(
        snapshot_weekly, snapshot_swings
    )

    snapshot_bos = consolidate_structural_breaks(
        snapshot_breaks, snapshot_swings
    )

    snapshot_retests = detect_daily_structural_retests(
        historical_daily,
        snapshot_bos,
        atr_period=14,
        tolerance_atr=0.25,
    )

    # Compare all BOS signals available by this historical cutoff.
    if not snapshot_weekly:
        raise AssertionError("No completed historical weekly candles")

    latest_completed_week = snapshot_weekly[-1]["datetime"]

    expected_bos_keys = {
        (b["date"], b["direction"])
        for b in weekly_bos
        if b["date"] <= latest_completed_week
    }

    reconstructed_bos_keys = {
        (b["date"], b["direction"])
        for b in snapshot_bos
    }

    assert reconstructed_bos_keys == expected_bos_keys, (
        f"Historical BOS set mismatch at {latest_completed_week}: "
        f"missing={expected_bos_keys - reconstructed_bos_keys}, "
        f"unexpected={reconstructed_bos_keys - expected_bos_keys}"
    )

    # Every historically available BOS must have a matching retest record.
    expected_retest_keys = {
        key for key in full_retests
        if (key[0], key[1]) in expected_bos_keys
    }

    reconstructed_retest_keys = {
        (r["bos_date"], r["direction"], r["level"])
        for r in snapshot_retests
    }

    assert reconstructed_retest_keys == expected_retest_keys, (
        f"Historical retest set mismatch at {latest_completed_week}: "
        f"missing={expected_retest_keys - reconstructed_retest_keys}, "
        f"unexpected={reconstructed_retest_keys - expected_retest_keys}"
    )


    for signal in snapshot_bos:
        key = (signal["date"], signal["direction"])
        assert key in full_signals, (
            f"Historical BOS disappeared: {key}"
        )

        for field in (
            "primary_level",
            "primary_level_date",
            "close",
            "levels_broken",
            "broken_levels",
        ):
            assert signal[field] == full_signals[key][field], (
                f"Historical BOS changed: {key}, field={field}"
            )

    for earlier in snapshot_retests:
        key = (
            earlier["bos_date"],
            earlier["direction"],
            earlier["level"],
        )

        assert key in full_retests, (
            f"Historical retest disappeared: {key}"
        )

        later = full_retests[key]

        for field in (
            "detected_date",
            "retest_type",
            "resolved_date",
            "status",
            "subsequently_invalidated",
            "invalidation_date",
        ):
            if field in ("status", "subsequently_invalidated",
                         "invalidation_date"):
                continue

            if earlier[field] is not None:
                assert earlier[field] == later[field], (
                    f"Historical retest changed: {key}, field={field}"
                )

        if earlier["resolved_date"] is not None:
            assert earlier["status"] == later["status"], (
                f"Historical resolution changed: {key}"
            )

        if earlier["subsequently_invalidated"]:
            assert later["subsequently_invalidated"], (
                f"Historical invalidation disappeared: {key}"
            )
            assert earlier["invalidation_date"] == later["invalidation_date"], (
                f"Historical invalidation date changed: {key}"
            )

    print(
        "PASS:", cutoff, "daily candles,",
        len(snapshot_weekly), "completed weeks,",
        len(snapshot_bos), "BOS signals,",
        len(snapshot_retests), "daily retests stable",
    )

print("PASS: End-to-end historical Gold replay validation")

# Historical monthly-zone replay using only completed monthly candles.

print("\nGOLD MONTHLY ZONE HISTORICAL STABILITY TEST")

full_monthly_classified = classify_structural_swings(
    monthly,
    strength=2,
    atr_period=14,
    major_threshold=2.0,
)

full_monthly_zones = track_monthly_zone_breaks(
    monthly,
    build_monthly_zones(full_monthly_classified),
)

print("\nGOLD MONTHLY ZONE BREAK DETAILS")

for zone in full_monthly_zones:
    print(
        zone["type"].upper(),
        "| Level:", round(zone["level"], 2),
        "| Zone:", round(zone["lower"], 2),
        "-", round(zone["upper"], 2),
        "| Status:", zone["status"].upper(),
        "| Swing:", zone["swing_date"],
        "| Confirmed:", zone["confirmed_at"],
        "| Broken:", zone["broken_at"],
        "| Break close:", zone["break_close"],
        "| Break confirmed:", zone["break_confirmed_at"],
    )

def monthly_zone_key(zone):
    return (
        zone["type"],
        zone["swing_date"],
        zone["confirmed_at"],
    )

full_zone_lookup = {
    monthly_zone_key(zone): zone
    for zone in full_monthly_zones
}

for cutoff in daily_cutoffs:
    historical_daily = daily[:cutoff]
    snapshot_date = date.fromisoformat(
        historical_daily[-1]["datetime"]
    )

    # A monthly candle becomes available only after month-end.
    as_of = snapshot_date + timedelta(days=1)

    snapshot_monthly = aggregate_ohlc(
        historical_daily,
        "monthly",
        as_of=as_of,
    )

    snapshot_classified = classify_structural_swings(
        snapshot_monthly,
        strength=2,
        atr_period=14,
        major_threshold=2.0,
    )

    snapshot_zones = track_monthly_zone_breaks(
        snapshot_monthly,
        build_monthly_zones(snapshot_classified),
        as_of=as_of,
    )

    snapshot_zone_keys = {
        monthly_zone_key(zone) for zone in snapshot_zones
    }

    expected_zone_keys = {
        monthly_zone_key(zone)
        for zone in full_monthly_zones
        if date.fromisoformat(zone["confirmed_at"][:10]).replace(
            day=1
        ) < as_of.replace(day=1)
    }

    if snapshot_zone_keys != expected_zone_keys:
        raise AssertionError(
            "Historical monthly-zone completeness mismatch: "
            f"missing={expected_zone_keys - snapshot_zone_keys}, "
            f"unexpected={snapshot_zone_keys - expected_zone_keys}"
        )

    for zone in snapshot_zones:
        key = monthly_zone_key(zone)

        if key not in full_zone_lookup:
            raise AssertionError(
                f"Historical monthly zone missing from full history: {key}"
            )

        full_zone = full_zone_lookup[key]

        for field in (
            "level",
            "lower",
            "upper",
            "atr_at_confirmation",
        ):
            if abs(zone[field] - full_zone[field]) > 1e-8:
                raise AssertionError(
                    f"Monthly zone {key} changed {field}"
                )

        if zone["status"] == "broken":
            for field in (
                "broken_at",
                "break_close",
                "break_confirmed_at",
            ):
                if zone[field] != full_zone[field]:
                    raise AssertionError(
                        f"Monthly zone {key} changed {field}"
                    )

        if (
            zone["break_confirmed_at"] is not None
            and zone["break_confirmed_at"] > as_of.isoformat()
        ):
            raise AssertionError(
                f"Future monthly break leaked into snapshot: {key}"
            )

    print(
        "PASS:", cutoff, "daily candles,",
        len(snapshot_monthly), "completed months,",
        len(snapshot_zones), "monthly zones stable",
        "| Support:", sum(z["type"] == "support" for z in snapshot_zones),
        "| Resistance:", sum(z["type"] == "resistance" for z in snapshot_zones),
        "| Broken:", sum(z["status"] == "broken" for z in snapshot_zones),
        "| Unbroken:", sum(z["status"] == "unbroken" for z in snapshot_zones),
    )

print("PASS: Historical Gold monthly-zone replay validation")
