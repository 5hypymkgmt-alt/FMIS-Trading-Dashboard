"""Export validated completed Gold daily candles for research."""

import json
import os
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

import requests

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
    raise RuntimeError(payload.get("message", "No Gold history"))

today = datetime.now(timezone.utc).date()
completed = []
seen = set()

for candle in candles:
    candle_date = datetime.fromisoformat(
        candle["datetime"][:10]
    ).date()

    if candle_date in seen:
        raise ValueError(f"Duplicate candle: {candle_date}")

    seen.add(candle_date)

    prices = [
        float(candle[field])
        for field in ("open", "high", "low", "close")
    ]

    o, h, l, c = prices

    if not all(isfinite(v) and v > 0 for v in prices):
        raise ValueError(f"Invalid OHLC: {candle_date}")

    if h < max(o, c, l) or l > min(o, c, h):
        raise ValueError(f"Inconsistent OHLC: {candle_date}")

    if candle_date < today:
        completed.append({
            "datetime": candle_date.isoformat(),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
        })

completed.sort(key=lambda x: x["datetime"])

if len(completed) < 200:
    raise RuntimeError("Insufficient completed Gold history")

output = {
    "market": "XAU/USD",
    "source": "Twelve Data",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "latest_completed_candle": completed[-1]["datetime"],
    "candle_count": len(completed),
    "candles": completed,
}

Path("gold_historical_candles.json").write_text(
    json.dumps(output, indent=2)
)

print("PASS: Gold historical candles exported")
print("Candles:", len(completed))
print("Earliest:", completed[0]["datetime"])
print("Latest:", completed[-1]["datetime"])
