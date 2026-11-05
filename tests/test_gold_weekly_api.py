"""Inspect Twelve Data's native weekly XAU/USD candles."""

import os
import requests

key = os.environ.get("PRICE_API_KEY")
assert key, "PRICE_API_KEY is missing"

response = requests.get(
    "https://api.twelvedata.com/time_series",
    params={
        "symbol": "XAU/USD",
        "interval": "1week",
        "outputsize": 25,
        "timezone": "UTC",
        "apikey": key,
        "format": "JSON",
    },
    timeout=25,
)

response.raise_for_status()
data = response.json()

assert "values" in data, (
    f"Weekly Gold API error: {data.get('message', data)}"
)

print("Weekly Gold metadata:", data.get("meta", {}))

for candle in data["values"][:8]:
    print(
        "Weekly Gold:",
        candle["datetime"],
        "| High:", candle["high"],
        "| Low:", candle["low"],
        "| Close:", candle["close"],
    )

print("PASS: Native weekly Gold candles retrieved")
