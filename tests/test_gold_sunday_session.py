"""Inspect historical XAU/USD hourly candles around Sunday opening."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from update import get_json

key = os.environ.get("PRICE_API_KEY")
assert key, "PRICE_API_KEY is missing"

data = get_json(
    "https://api.twelvedata.com/time_series",
    {
        "symbol": "XAU/USD",
        "interval": "1h",
        "start_date": "2026-11-01 00:00:00",
        "end_date": "2026-11-03 00:00:00",
        "timezone": "UTC",
        "outputsize": 60,
        "apikey": key,
        "format": "JSON",
    },
)

assert "values" in data, (
    f"Gold hourly API error: {data.get('message', data)}"
)

print("API metadata:", data.get("meta", {}))

for candle in sorted(data["values"], key=lambda x: x["datetime"]):
    print(
        "Gold hourly:",
        candle["datetime"],
        "| Open:", candle["open"],
        "| Close:", candle["close"],
    )

print("PASS: Historical Gold hourly data retrieved")
