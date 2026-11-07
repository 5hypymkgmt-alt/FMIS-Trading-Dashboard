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
)

from gold_daily_retests import detect_daily_structural_retests

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
