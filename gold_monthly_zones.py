"""Monthly structural support and resistance zones for Gold."""


def build_monthly_zones(classified_swings, atr_fraction=0.25):
    """Build ATR-based zones from confirmed major monthly swings."""

    if not 0 < atr_fraction <= 1:
        raise ValueError("ATR fraction must be between 0 and 1")

    zones = []

    for swing in classified_swings:
        if (
            swing.get("classification") != "major"
            or swing.get("structural_status") != "confirmed"
        ):
            continue

        atr = swing.get("atr_at_confirmation")

        if atr is None or float(atr) <= 0:
            continue

        price = float(swing["price"])
        half_width = float(atr) * atr_fraction

        zones.append({
            "type": (
                "resistance"
                if swing["type"] == "high"
                else "support"
            ),
            "swing_date": swing["date"],
            "confirmed_at": swing["confirmed_at"],
            "level": price,
            "lower": price - half_width,
            "upper": price + half_width,
            "atr_at_confirmation": float(atr),
            "status": "unbroken",
        })

    return sorted(
        zones,
        key=lambda zone: (
            zone["confirmed_at"],
            zone["swing_date"],
        ),
    )


def track_monthly_zone_breaks(monthly_candles, zones, as_of=None):
    """Track confirmed monthly closing breaks at a historical cutoff."""

    from datetime import date, datetime, timezone

    if as_of is None:
        as_of = datetime.now(timezone.utc).date()
    elif isinstance(as_of, datetime):
        as_of = as_of.date()
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    ordered = sorted(
        (
            candle for candle in monthly_candles
            if is_completed_monthly_candle(candle, as_of)
        ),
        key=lambda candle: candle["datetime"],
    )

    results = []

    for zone in zones:
        result = zone.copy()
        result["status"] = "unbroken"
        result["broken_at"] = None
        result["break_close"] = None
        result["break_confirmed_at"] = None

        for candle in ordered:
            candle_date = candle["datetime"]

            # A zone cannot break before or on its confirmation candle.
            if candle_date <= zone["confirmed_at"]:
                continue

            close = float(candle["close"])

            if zone["type"] == "resistance":
                broken = close > float(zone["upper"])
            elif zone["type"] == "support":
                broken = close < float(zone["lower"])
            else:
                raise ValueError("Unknown monthly zone type")

            if broken:
                result["status"] = "broken"
                result["broken_at"] = candle_date
                result["break_close"] = close

                month = date.fromisoformat(candle_date[:10])
                result["break_confirmed_at"] = (
                    date(month.year + 1, 1, 1)
                    if month.month == 12
                    else date(month.year, month.month + 1, 1)
                ).isoformat()
                break

        results.append(result)

    return results


def is_completed_monthly_candle(candle, as_of):
    """Check whether a monthly candle is completed at a UTC date."""

    from datetime import date, datetime

    if isinstance(as_of, datetime):
        as_of = as_of.date()
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    month = date.fromisoformat(str(candle["datetime"])[:10])
    month_start = month.replace(day=1)
    current_month = as_of.replace(day=1)

    return month_start < current_month
