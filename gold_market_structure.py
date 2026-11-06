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
