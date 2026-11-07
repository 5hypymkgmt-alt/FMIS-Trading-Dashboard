"""Unified Gold Market Structure Intelligence.

Phase 2: Structural analysis only.
Trade Confidence and Trade Readiness remain unchanged.
"""

from datetime import date, datetime, timezone

from gold_market_structure import (
    aggregate_ohlc,
    classify_structural_swings,
    select_alternating_major_swings,
    detect_structural_breaks,
    consolidate_structural_breaks,
    classify_weekly_market_bias,
    detect_structural_retests,
)
from gold_monthly_zones import (
    build_monthly_zones,
    track_monthly_zone_breaks,
)
from gold_daily_retests import detect_daily_structural_retests


def build_gold_structure_intelligence(daily_candles, as_of=None):
    """Build Gold structure using completed historical candles only."""

    if as_of is None:
        as_of = datetime.now(timezone.utc).date()
    elif isinstance(as_of, datetime):
        as_of = as_of.date()
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    completed_daily = sorted(
        (
            candle for candle in daily_candles
            if date.fromisoformat(str(candle["datetime"])[:10]) < as_of
        ),
        key=lambda candle: candle["datetime"],
    )

    weekly = aggregate_ohlc(
        completed_daily, "weekly", as_of=as_of
    )
    monthly = aggregate_ohlc(
        completed_daily, "monthly", as_of=as_of
    )

    monthly_swings = classify_structural_swings(
        monthly,
        strength=2,
        atr_period=14,
        major_threshold=2.0,
    )

    monthly_zones = build_monthly_zones(
        monthly_swings,
        atr_fraction=0.25,
    )

    monthly_zones = track_monthly_zone_breaks(
        monthly,
        monthly_zones,
        as_of=as_of,
    )

    weekly_swings = classify_structural_swings(
        weekly,
        strength=2,
        atr_period=14,
        major_threshold=2.0,
    )

    weekly_break_events = detect_structural_breaks(
        weekly,
        weekly_swings,
    )

    weekly_bos = consolidate_structural_breaks(
        weekly_break_events,
        weekly_swings,
    )

    weekly_major_swings = select_alternating_major_swings(
        weekly_swings,
    )

    weekly_bias = classify_weekly_market_bias(
        weekly_major_swings,
        weekly_bos,
    )

    weekly_retests = detect_structural_retests(
        weekly,
        weekly_bos,
        atr_period=14,
        tolerance_atr=0.25,
    )

    daily_retests = detect_daily_structural_retests(
        completed_daily,
        weekly_bos,
        atr_period=14,
        tolerance_atr=0.25,
    )

    return {
        "market": "XAU/USD",
        "as_of": as_of.isoformat(),
        "daily_candle_count": len(completed_daily),
        "weekly_candle_count": len(weekly),
        "monthly_candle_count": len(monthly),
        "monthly": {
            "zones": monthly_zones,
            "support": [
                z for z in monthly_zones
                if z["type"] == "support"
            ],
            "resistance": [
                z for z in monthly_zones
                if z["type"] == "resistance"
            ],
            "broken_count": sum(
                z["status"] == "broken"
                for z in monthly_zones
            ),
            "unbroken_count": sum(
                z["status"] == "unbroken"
                for z in monthly_zones
            ),
        },
        "weekly": {
            "bias": weekly_bias,
            "major_swings": weekly_major_swings,
            "bos": weekly_bos,
            "bos_count": len(weekly_bos),
            "retests": weekly_retests,
            "retest_count": len(weekly_retests),
        },
        "daily": {
            "retests": daily_retests,
            "retest_count": len(daily_retests),
            "confirmed_count": sum(
                r["status"] == "confirmed"
                for r in daily_retests
            ),
            "failed_count": sum(
                r["status"] == "failed"
                for r in daily_retests
            ),
            "invalidated_count": sum(
                r["subsequently_invalidated"]
                for r in daily_retests
            ),
        },
    }
