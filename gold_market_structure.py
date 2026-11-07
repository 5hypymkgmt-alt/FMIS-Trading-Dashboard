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

            # A trading week is complete after Friday.
            # Saturday and Sunday must include the previous Friday close.
            if as_of.weekday() >= 5:
                current_period += __import__("datetime").timedelta(days=7)
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


def label_primary_structure(classified_swings):
    """Label major swings HH, HL, LH or LL without using future swings."""
    previous_major = {"high": None, "low": None}
    labelled = []

    ordered = sorted(
        classified_swings,
        key=lambda swing: (
            swing["confirmed_at"],
            swing["date"],
            swing["type"],
        ),
    )

    for swing in ordered:
        item = swing.copy()
        item["structure_label"] = None

        if (
            item["classification"] == "major"
            and item["structural_status"] == "confirmed"
        ):
            swing_type = item["type"]
            previous = previous_major[swing_type]

            if previous is not None:
                if item["price"] > previous["price"]:
                    item["structure_label"] = (
                        "HH" if swing_type == "high" else "HL"
                    )
                elif item["price"] < previous["price"]:
                    item["structure_label"] = (
                        "LH" if swing_type == "high" else "LL"
                    )
                else:
                    item["structure_label"] = "EQH" if swing_type == "high" else "EQL"

            previous_major[swing_type] = item

        labelled.append(item)

    return labelled


def select_alternating_major_swings(classified_swings):
    """Select alternating major pivots using confirmation-time ordering.

    The returned sequence is a current structural snapshot, not an
    immutable history of previously published signals.
    """
    ordered = sorted(
        (
            swing.copy()
            for swing in classified_swings
            if swing["classification"] == "major"
            and swing["structural_status"] == "confirmed"
        ),
        key=lambda swing: (
            swing["confirmed_at"],
            swing["date"],
            swing["type"],
        ),
    )

    selected = []

    for swing in ordered:
        if not selected or swing["type"] != selected[-1]["type"]:
            selected.append(swing)
            continue

        previous = selected[-1]

        more_extreme = (
            swing["price"] > previous["price"]
            if swing["type"] == "high"
            else swing["price"] < previous["price"]
        )

        if more_extreme:
            selected[-1] = swing

    return selected


def track_major_swing_events(classified_swings):
    """Record confirmed major pivots and later supersession events.

    Events are ordered by confirmation time. Historical events are
    preserved even when a more extreme same-type pivot replaces one.
    """
    ordered = sorted(
        (
            swing.copy()
            for swing in classified_swings
            if swing["classification"] == "major"
            and swing["structural_status"] == "confirmed"
        ),
        key=lambda swing: (
            swing["confirmed_at"],
            swing["date"],
            swing["type"],
        ),
    )

    events = []
    active = []

    for swing in ordered:
        if not active or swing["type"] != active[-1]["type"]:
            active.append(swing)
            events.append({
                "event": "confirmed",
                "recorded_at": swing["confirmed_at"],
                "swing": swing.copy(),
            })
            continue

        previous = active[-1]

        more_extreme = (
            swing["price"] > previous["price"]
            if swing["type"] == "high"
            else swing["price"] < previous["price"]
        )

        events.append({
            "event": "confirmed",
            "recorded_at": swing["confirmed_at"],
            "swing": swing.copy(),
        })

        if more_extreme:
            events.append({
                "event": "superseded",
                "recorded_at": swing["confirmed_at"],
                "swing": previous.copy(),
                "replaced_by": swing.copy(),
            })
            active[-1] = swing

    return events


def detect_structural_breaks(candles, classified_swings):
    """Detect first weekly closing break of each confirmed major swing level."""

    ordered = sorted(candles, key=lambda c: c["datetime"])
    levels = sorted(
        (
            s for s in classified_swings
            if s["classification"] == "major"
            and s["structural_status"] == "confirmed"
        ),
        key=lambda s: (s["confirmed_at"], s["date"], s["type"]),
    )

    events = []
    broken = set()

    for candle in ordered:
        candle_date = candle["datetime"]
        close = float(candle["close"])

        for swing in levels:
            identity = (swing["type"], swing["date"], swing["price"])

            if identity in broken or candle_date <= swing["confirmed_at"]:
                continue

            price = float(swing["price"])
            direction = (
                "bullish" if swing["type"] == "high" else "bearish"
            )

            if (
                (direction == "bullish" and close > price)
                or (direction == "bearish" and close < price)
            ):
                events.append({
                    "date": candle_date,
                    "direction": direction,
                    "level_date": swing["date"],
                    "level_price": price,
                    "close": close,
                })
                broken.add(identity)

    return events


def consolidate_structural_breaks(events, classified_swings):
    """Group same-week, same-direction breaks into one primary signal."""

    confirmation_dates = {
        (s["type"], s["date"], float(s["price"])): s["confirmed_at"]
        for s in classified_swings
        if s["classification"] == "major"
        and s["structural_status"] == "confirmed"
    }

    grouped = {}

    for event in events:
        key = (event["date"], event["direction"])
        grouped.setdefault(key, []).append(event)

    signals = []

    for (event_date, direction), group in sorted(grouped.items()):
        swing_type = "high" if direction == "bullish" else "low"

        primary = max(
            group,
            key=lambda e: (
                confirmation_dates[
                    (swing_type, e["level_date"], float(e["level_price"]))
                ],
                e["level_date"],
            ),
        )

        signals.append({
            "date": event_date,
            "direction": direction,
            "primary_level": primary["level_price"],
            "primary_level_date": primary["level_date"],
            "close": primary["close"],
            "levels_broken": len(group),
            "broken_levels": sorted(
                e["level_price"] for e in group
            ),
        })

    return signals


def classify_weekly_market_bias(alternating_swings, bos_signals):
    """Classify weekly bias from confirmed major structure and BOS."""

    highs = [
        s for s in alternating_swings
        if s["type"] == "high"
    ]
    lows = [
        s for s in alternating_swings
        if s["type"] == "low"
    ]

    if len(highs) < 2 or len(lows) < 2 or not bos_signals:
        return {
            "bias": "Neutral",
            "reason": "Insufficient confirmed structural evidence",
        }

    higher_high = highs[-1]["price"] > highs[-2]["price"]
    higher_low = lows[-1]["price"] > lows[-2]["price"]

    lower_high = highs[-1]["price"] < highs[-2]["price"]
    lower_low = lows[-1]["price"] < lows[-2]["price"]

    latest_bos = bos_signals[-1]["direction"]

    if higher_high and higher_low and latest_bos == "bullish":
        bias = "Bullish"
    elif lower_high and lower_low and latest_bos == "bearish":
        bias = "Bearish"
    else:
        bias = "Neutral"

    return {
        "bias": bias,
        "higher_high": higher_high,
        "higher_low": higher_low,
        "lower_high": lower_high,
        "lower_low": lower_low,
        "latest_bos": latest_bos,
        "latest_bos_date": bos_signals[-1]["date"],
        "latest_swing_high": highs[-1]["price"],
        "latest_swing_low": lows[-1]["price"],
    }


def detect_structural_retests(
    candles,
    bos_signals,
    atr_period=14,
    tolerance_atr=0.25,
):
    """Track retests, confirmation and subsequent invalidation."""

    if tolerance_atr <= 0:
        raise ValueError("Retest tolerance must be positive")

    ordered = sorted(candles, key=lambda c: c["datetime"])
    atr_series = calculate_atr_series(ordered, atr_period)
    atr_by_date = {
        item["datetime"]: item["atr"]
        for item in atr_series
    }

    results = []

    for bos in sorted(
        bos_signals,
        key=lambda event: (event["date"], event["direction"]),
    ):
        direction = bos["direction"]

        if direction not in ("bullish", "bearish"):
            raise ValueError("Invalid BOS direction")

        level = float(bos["primary_level"])

        result = {
            "bos_date": bos["date"],
            "direction": direction,
            "level": level,
            "level_date": bos["primary_level_date"],
            "status": "awaiting_retest",
            "detected_date": None,
            "resolved_date": None,
            "atr_at_retest": None,
            "tolerance": None,
            "latest_close": None,
            "subsequently_invalidated": False,
            "invalidation_date": None,
        }

        detected = False
        confirmed = False

        for candle in ordered:
            candle_date = candle["datetime"]

            if candle_date <= bos["date"]:
                continue

            atr = atr_by_date.get(candle_date)

            if atr is None or atr <= 0:
                continue

            high = float(candle["high"])
            low = float(candle["low"])
            close = float(candle["close"])

            if not detected:
                tolerance = atr * tolerance_atr
                zone_low = level - tolerance
                zone_high = level + tolerance

                touched = (
                    low <= zone_high
                    and high >= zone_low
                )

                if not touched:
                    continue

                detected = True

                result.update({
                    "status": "detected",
                    "detected_date": candle_date,
                    "atr_at_retest": atr,
                    "tolerance": tolerance,
                })

            result["latest_close"] = close

            if not confirmed:
                if direction == "bullish":
                    if close > level:
                        result["status"] = "confirmed"
                        result["resolved_date"] = candle_date
                        confirmed = True
                    elif close < level:
                        result["status"] = "failed"
                        result["resolved_date"] = candle_date
                        break
                else:
                    if close < level:
                        result["status"] = "confirmed"
                        result["resolved_date"] = candle_date
                        confirmed = True
                    elif close > level:
                        result["status"] = "failed"
                        result["resolved_date"] = candle_date
                        break

            else:
                invalidated = (
                    close < level
                    if direction == "bullish"
                    else close > level
                )

                if invalidated:
                    result["subsequently_invalidated"] = True
                    result["invalidation_date"] = candle_date
                    break

        results.append(result)

    return results
