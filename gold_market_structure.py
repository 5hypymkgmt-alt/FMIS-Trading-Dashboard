"""Independent higher-timeframe market structure tools for Gold."""

from datetime import date, datetime, timezone


def aggregate_ohlc(daily_candles, timeframe, as_of=None):
    """Aggregate completed daily candles into completed weeks or months."""
    if timeframe not in ("weekly", "monthly"):
        raise ValueError("Timeframe must be weekly or monthly")

    if as_of is None:
        as_of = datetime.now(timezone.utc).date()

    if isinstance(as_of, datetime):
        as_of = as_of.date()

    grouped = {}

    for candle in daily_candles:
        day = date.fromisoformat(str(candle["datetime"])[:10])

        if day >= as_of:
            continue

        if timeframe == "weekly":
            period = day - __import__("datetime").timedelta(
                days=day.weekday()
            )
            current_period = as_of - __import__("datetime").timedelta(
                days=as_of.weekday()
            )
        else:
            period = day.replace(day=1)
            current_period = as_of.replace(day=1)

        if period >= current_period:
            continue

        grouped.setdefault(period, []).append((day, candle))

    result = []

    for period, items in sorted(grouped.items()):
        items.sort(key=lambda item: item[0])
        candles = [item[1] for item in items]

        result.append({
            "datetime": period.isoformat(),
            "open": float(candles[0]["open"]),
            "high": max(float(c["high"]) for c in candles),
            "low": min(float(c["low"]) for c in candles),
            "close": float(candles[-1]["close"]),
            "daily_candles": len(candles),
        })

    return result


def detect_confirmed_swings(candles, strength=2):
    """Find confirmed swing highs and lows in completed OHLC candles."""
    if not isinstance(strength, int) or isinstance(strength, bool) or strength < 1:
        raise ValueError("Strength must be a positive integer")

    ordered = sorted(candles, key=lambda c: c["datetime"])
    swings = []

    for i in range(strength, len(ordered) - strength):
        candidate = ordered[i]
        before = ordered[i - strength:i]
        after = ordered[i + 1:i + strength + 1]
        confirmation_date = ordered[i + strength]["datetime"]

        high = float(candidate["high"])
        low = float(candidate["low"])

        if all(high > float(c["high"]) for c in before + after):
            swings.append({
                "type": "high",
                "date": candidate["datetime"],
                "price": high,
                "confirmed_at": confirmation_date,
            })

        if all(low < float(c["low"]) for c in before + after):
            swings.append({
                "type": "low",
                "date": candidate["datetime"],
                "price": low,
                "confirmed_at": confirmation_date,
            })

    return swings


def calculate_atr(candles, period=14):
    """Calculate Wilder ATR from chronological completed OHLC candles."""
    if not isinstance(period, int) or isinstance(period, bool) or period < 1:
        raise ValueError("ATR period must be a positive integer")

    ordered = sorted(candles, key=lambda c: c["datetime"])

    if len(ordered) < period + 1:
        raise ValueError("Insufficient candles for ATR calculation")

    true_ranges = []

    for i in range(1, len(ordered)):
        high = float(ordered[i]["high"])
        low = float(ordered[i]["low"])
        previous_close = float(ordered[i - 1]["close"])

        tr = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )
        true_ranges.append(tr)

    atr = sum(true_ranges[:period]) / period

    for tr in true_ranges[period:]:
        atr = ((atr * (period - 1)) + tr) / period

    return atr


def calculate_atr_series(candles, period=14):
    """Return Wilder ATR values aligned with completed candles."""
    if not isinstance(period, int) or isinstance(period, bool) or period < 1:
        raise ValueError("ATR period must be a positive integer")

    ordered = sorted(candles, key=lambda c: c["datetime"])
    result = []

    for i, candle in enumerate(ordered):
        if i < period:
            atr = None
        else:
            atr = calculate_atr(ordered[:i + 1], period)

        result.append({
            "datetime": candle["datetime"],
            "atr": atr,
        })

    return result


def classify_structural_swings(candles, strength=2, atr_period=14,
                               major_threshold=2.0):
    """Classify immutable confirmed swings, excluding ambiguous pivots."""
    if major_threshold <= 0:
        raise ValueError("Major threshold must be positive")

    swings = detect_confirmed_swings(candles, strength)
    atr_series = calculate_atr_series(candles, atr_period)

    atr_by_date = {
        item["datetime"]: item["atr"]
        for item in atr_series
    }

    ordered = sorted(
        swings,
        key=lambda item: (
            item["confirmed_at"],
            item["date"],
            item["type"],
        ),
    )

    classified = []
    previous_opposite = {"high": None, "low": None}

    by_swing_date = {}

    for swing in ordered:
        by_swing_date.setdefault(swing["date"], []).append(swing)

    for swing_date in sorted(
        by_swing_date,
        key=lambda day: (
            by_swing_date[day][0]["confirmed_at"],
            day,
        ),
    ):
        group = by_swing_date[swing_date]
        types = {item["type"] for item in group}

        if types == {"high", "low"}:
            for swing in group:
                item = swing.copy()
                item["atr_at_confirmation"] = atr_by_date.get(
                    swing["confirmed_at"]
                )
                item["distance_atr"] = None
                item["classification"] = "ambiguous"
                item["structural_status"] = "ambiguous_same_candle"
                classified.append(item)

            previous_opposite = {"high": None, "low": None}
            continue

        for swing in group:
            item = swing.copy()
            atr = atr_by_date.get(swing["confirmed_at"])

            opposite_type = (
                "low" if swing["type"] == "high" else "high"
            )
            opposite = previous_opposite[opposite_type]

            item["atr_at_confirmation"] = atr
            item["distance_atr"] = None
            item["classification"] = "unclassified"
            item["structural_status"] = "confirmed"

            if atr is not None and atr > 0 and opposite is not None:
                distance = abs(swing["price"] - opposite["price"])
                item["distance_atr"] = distance / atr

                item["classification"] = (
                    "major"
                    if item["distance_atr"] >= major_threshold
                    else "minor"
                )

            classified.append(item)
            previous_opposite[swing["type"]] = swing

    return classified
