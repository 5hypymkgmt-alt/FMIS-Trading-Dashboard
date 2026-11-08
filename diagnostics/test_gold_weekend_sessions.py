"""Investigate Twelve Data Gold weekend candle sessions."""

import os
import requests

API = "https://api.twelvedata.com/time_series"
KEY = os.getenv("PRICE_API_KEY")

if not KEY:
    raise RuntimeError("PRICE_API_KEY is missing")

def fetch(params):
    params["apikey"] = KEY
    response = requests.get(API, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(data.get("message"))

    return data

print("\n=== XAU/USD DAILY METADATA ===")

daily = fetch({
    "symbol": "XAU/USD",
    "interval": "1day",
    "outputsize": 12,
    "format": "JSON",
})

print("Metadata:", daily.get("meta"))

print("\n=== RECENT DAILY CANDLES ===")

for candle in reversed(daily.get("values", [])):
    print(candle)

periods = [
    ("16-19 October", "2026-10-16T00:00:00",
     "2026-10-19T23:59:59"),
    ("23-26 October", "2026-10-23T00:00:00",
     "2026-10-26T23:59:59"),
]

for label, start, end in periods:
    print(f"\n=== HOURLY DATA: {label} ===")

    hourly = fetch({
        "symbol": "XAU/USD",
        "interval": "1h",
        "start_date": start,
        "end_date": end,
        "format": "JSON",
    })

    print("Metadata:", hourly.get("meta"))

    values = sorted(
        hourly.get("values", []),
        key=lambda x: x["datetime"]
    )

    print("Hourly candles returned:", len(values))

    for candle in values:
        print(
            candle["datetime"],
            "O:", candle["open"],
            "H:", candle["high"],
            "L:", candle["low"],
            "C:", candle["close"]
        )

print("\nPASS: Weekend session diagnostic completed")
