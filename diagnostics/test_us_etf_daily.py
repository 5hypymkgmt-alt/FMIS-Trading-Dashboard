"""Inspect Twelve Data daily candle dates for SPY and QQQ."""

import datetime
import os
import requests

from update import filter_completed_session_candles

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

    print("\n", symbol, "API metadata:")
    metadata = data.get("meta", {})
    for field in (
        "symbol", "name", "exchange",
        "mic_code", "type", "timezone",
        "currency", "interval"
    ):
        print(field + ":", metadata.get(field, "Not supplied"))

    print("\n", symbol, "daily candles:")

    for candle in data["values"]:
        print(
            candle["datetime"],
            "| Close:", candle["close"]
        )

    accepted = filter_completed_session_candles(data["values"], now)
    accepted_dates = {c["datetime"] for c in accepted}
    rejected = [
        c for c in data["values"]
        if c["datetime"] not in accepted_dates
    ]

    print("Accepted completed sessions:")
    for candle in accepted:
        print(candle["datetime"], "| Close:", candle["close"])

    print("Rejected sessions:")
    for candle in rejected:
        print(candle["datetime"], "| Close:", candle["close"])

    pre_close = datetime.datetime(
        2026, 11, 6, 20, 59,
        tzinfo=datetime.timezone.utc
    )
    pre_close_result = filter_completed_session_candles(
        data["values"], pre_close
    )
    assert all(
        c["datetime"][:10] != "2026-11-06"
        for c in pre_close_result
    ), f"{symbol}: unfinished session was accepted"

    print("PASS: Pre-close session excluded")
    if accepted:
        latest = max(accepted, key=lambda c: c["datetime"])
        print("Latest accepted:", latest["datetime"],
              "| Close:", latest["close"])

print("\nNOTE: Session completion does not prove provider settlement.")
