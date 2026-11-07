"""Retrieve and validate completed Gold candles for FMIS Market Structure."""

import os
from datetime import datetime, timezone
from math import isfinite

import requests

from gold_structure_intelligence import build_gold_structure_intelligence


def fetch_gold_structure():
    key = os.getenv("PRICE_API_KEY")
    if not key:
        raise RuntimeError("PRICE_API_KEY is missing")

    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": "XAU/USD",
            "interval": "1day",
            "outputsize": 1000,
            "timezone": "UTC",
            "apikey": key,
            "format": "JSON",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    candles = payload.get("values", [])
    if not candles:
        raise RuntimeError(
            payload.get("message", "No Gold history returned")
        )

    today = datetime.now(timezone.utc).date()
    seen = set()
    completed = []

    for candle in candles:
        candle_date = datetime.fromisoformat(
            str(candle["datetime"])[:10]
        ).date()

        if candle_date in seen:
            raise ValueError(f"Duplicate Gold candle: {candle_date}")
        seen.add(candle_date)

        prices = [
            float(candle[field])
            for field in ("open", "high", "low", "close")
        ]
        o, h, l, c = prices

        if not all(isfinite(v) and v > 0 for v in prices):
            raise ValueError(f"Invalid Gold prices: {candle_date}")
        if h < max(o, c, l) or l > min(o, c, h):
            raise ValueError(f"Inconsistent Gold OHLC: {candle_date}")

        if candle_date < today:
            completed.append(candle)

    if not completed:
        raise RuntimeError("No completed Gold candles available")

    result = build_gold_structure_intelligence(
        completed, as_of=today
    )
    result["status"] = "ok"
    result["latest_daily_candle"] = max(
        candle["datetime"][:10] for candle in completed
    )
    return result
