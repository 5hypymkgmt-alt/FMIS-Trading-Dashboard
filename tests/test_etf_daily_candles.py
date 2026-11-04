"""Diagnostic for FMIS SPY and QQQ daily candles."""

import os
import json
import urllib.parse
import urllib.request
import datetime

key = os.getenv("PRICE_API_KEY", "")

if not key:
    raise SystemExit("PRICE_API_KEY is unavailable")

print("Diagnostic UTC time:", datetime.datetime.now(
    datetime.timezone.utc).isoformat())

for name, symbol in [
    ("S&P 500 ETF", "SPY"),
    ("Nasdaq 100 ETF", "QQQ"),
]:
    params = urllib.parse.urlencode({
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 5,
        "apikey": key,
    })

    url = "https://api.twelvedata.com/time_series?" + params

    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            data = json.load(response)

        print("\n", name, "|", symbol)
        print("API status:", data.get("status", "unknown"))
        print("Timezone:", data.get("meta", {}).get("exchange_timezone"))
        print("Message:", data.get("message", ""))

        for candle in data.get("values", []):
            print(
                candle.get("datetime"),
                "| Open:", candle.get("open"),
                "| Close:", candle.get("close"),
            )

    except Exception as exc:
        print(name, "| REQUEST FAILED:", str(exc)[:200])
