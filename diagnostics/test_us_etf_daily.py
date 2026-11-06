"""Inspect Twelve Data daily candle dates for SPY and QQQ."""

import datetime
import os
import requests

API = 'https://api.twelvedata.com/time_series'
KEY = os.environ["PRICE_API_KEY"]

now = datetime.datetime.now(datetime.timezone.utc)
print("Diagnostic time:", now.isoformat())

for symbol in ("SPY", "QQQ"):
    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 3,
        "timezone": "America/New_York",
        "apikey": KEY,
        "format": "JSON",
    }

    response = requests.get(API, params=params, timeout=25)
    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        raise RuntimeError(
            f"{symbol}: {data.get('message', 'No candle data')}"
        )

    print("\n", symbol, "daily candles:")

    for candle in data["values"]:
        print(
            candle["datetime"],
            "| Close:", candle["close"]
        )

print("\nNOTE: Candle dates do not prove final settlement.")
