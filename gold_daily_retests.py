"""Daily retests of confirmed weekly Gold structure."""

from datetime import date, timedelta

from gold_market_structure import calculate_atr_series


def detect_daily_structural_retests(
    daily_candles,
    weekly_bos,
    atr_period=14,
    tolerance_atr=0.25,
):
    """Track daily retests after confirmed weekly BOS events."""

    if tolerance_atr <= 0:
        raise ValueError("Retest tolerance must be positive")

    ordered = sorted(
        daily_candles, key=lambda c: c["datetime"]
    )

    atr_by_date = {
        item["datetime"]: item["atr"]
        for item in calculate_atr_series(ordered, atr_period)
    }

    results = []

    for bos in sorted(weekly_bos, key=lambda b: b["date"]):
        direction = bos["direction"]

        if direction not in ("bullish", "bearish"):
            raise ValueError("Invalid BOS direction")

        level = float(bos["primary_level"])
        first_eligible = (
            date.fromisoformat(bos["date"])
            + timedelta(days=7)
        )

        result = {
            "bos_date": bos["date"],
            "direction": direction,
            "level": level,
            "first_eligible_date": first_eligible.isoformat(),
            "status": "awaiting_retest",
            "retest_type": None,
            "detected_date": None,
            "resolved_date": None,
            "atr_at_retest": None,
            "tolerance": None,
            "latest_close": None,
            "subsequently_invalidated": False,
            "invalidation_date": None,
        }

        for candle in ordered:
            candle_date = candle["datetime"]

            if date.fromisoformat(candle_date) < first_eligible:
                continue

            atr = atr_by_date.get(candle_date)

            if atr is None or atr <= 0:
                continue

            high = float(candle["high"])
            low = float(candle["low"])
            close = float(candle["close"])
            opening = float(candle["open"])
            tolerance = atr * tolerance_atr

            if result["detected_date"] is None:
                exact_touch = low <= level <= high

                if direction == "bullish":
                    correct_side = opening > level
                    zone_approach = (
                        low > level
                        and low <= level + tolerance
                    )
                else:
                    correct_side = opening < level
                    zone_approach = (
                        high < level
                        and high >= level - tolerance
                    )

                if not correct_side:
                    continue

                if not (exact_touch or zone_approach):
                    continue

                result.update({
                    "status": "detected",
                    "retest_type": (
                        "exact_level"
                        if exact_touch
                        else "zone_approach"
                    ),
                    "detected_date": candle_date,
                    "atr_at_retest": atr,
                    "tolerance": tolerance,
                })

            result["latest_close"] = close

            if result["resolved_date"] is not None:
                if result["status"] == "confirmed":
                    invalidated = (
                        (direction == "bullish" and close < level)
                        or (direction == "bearish" and close > level)
                    )
                    if invalidated:
                        result["subsequently_invalidated"] = True
                        result["invalidation_date"] = candle_date
                        break
                continue

            if direction == "bullish":
                if close > level:
                    result["status"] = "confirmed"
                elif close < level:
                    result["status"] = "failed"
            else:
                if close < level:
                    result["status"] = "confirmed"
                elif close > level:
                    result["status"] = "failed"

            if result["status"] in ("confirmed", "failed"):
                result["resolved_date"] = candle_date

        results.append(result)

    return results
