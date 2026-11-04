"""Test genuine XAU/USD prices using the FMIS calculation engine."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from update import prices

result = prices("XAU/USD")

print("Gold price status:", result.get("status"))
print("Gold price date:", result.get("date"))
print("Gold closing price:", result.get("close"))

assert result.get("status") in ("ok", "stale"), (
    f"XAU/USD price processing failed: {result.get('reason', result)}"
)

fields = (
    "close",
    "ema20",
    "ema50",
    "ema200",
    "rsi14",
    "adx14",
    "weekly_pivot",
    "confluence_score",
)

for field in fields:
    value = result.get(field)
    assert isinstance(value, (int, float)), f"{field} missing or nonnumeric"
    assert math.isfinite(value), f"{field} is not finite"
    print(f"{field}: {value}")

assert result["close"] > 0
assert 0 <= result["rsi14"] <= 100
assert result["adx14"] >= 0
assert -4 <= result["confluence_score"] <= 4

print("PASS: XAU/USD FMIS price calculations")

# Diagnostic: inspect raw Twelve Data candle dates.
import os
import datetime
from update import get_json

print("\n--- XAU/USD candle timestamp diagnostic ---")
print("GitHub UTC time:", datetime.datetime.now(datetime.timezone.utc).isoformat())

raw = get_json(
    "https://api.twelvedata.com/time_series",
    {
        "symbol": "XAU/USD",
        "interval": "1day",
        "outputsize": 3,
        "apikey": os.environ["PRICE_API_KEY"],
        "format": "JSON",
    },
)

assert "values" in raw, f"Timestamp diagnostic failed: {raw.get('message', raw)}"

print("API timezone:", raw.get("meta", {}).get("exchange_timezone", "Not supplied"))

for candle in raw["values"]:
    print("Candle:", candle["datetime"], "| Close:", candle["close"])

# Diagnostic: inspect the full API metadata.
import json
print("\n--- Twelve Data metadata ---")
print(json.dumps(raw.get("meta", {}), indent=2))

# Diagnostic: test whether end_date excludes the developing candle.
print("\n--- XAU/USD end_date diagnostic ---")

utc_yesterday = (
    datetime.datetime.now(datetime.timezone.utc).date()
    - datetime.timedelta(days=1)
)

restricted = get_json(
    "https://api.twelvedata.com/time_series",
    {
        "symbol": "XAU/USD",
        "interval": "1day",
        "outputsize": 3,
        "end_date": utc_yesterday.isoformat(),
        "apikey": os.environ["PRICE_API_KEY"],
        "format": "JSON",
    },
)

print("Requested end_date:", utc_yesterday.isoformat())
assert "values" in restricted, (
    f"Date-restricted diagnostic failed: {restricted.get('message', restricted)}"
)

for candle in restricted["values"]:
    print("Restricted candle:", candle["datetime"], "| Close:", candle["close"])

# Diagnostic: test an explicit UTC end_date boundary.
print("\n--- XAU/USD explicit UTC boundary diagnostic ---")

boundary_date = datetime.datetime.now(
    datetime.timezone.utc
).date()

boundary = get_json(
    "https://api.twelvedata.com/time_series",
    {
        "symbol": "XAU/USD",
        "interval": "1day",
        "outputsize": 5,
        "end_date": boundary_date.isoformat() + " 00:00:00",
        "timezone": "UTC",
        "apikey": os.environ["PRICE_API_KEY"],
        "format": "JSON",
    },
)

print("Requested UTC boundary:", boundary_date.isoformat(), "00:00:00")

if "values" in boundary:
    for candle in boundary["values"]:
        print(
            "UTC boundary candle:",
            candle["datetime"],
            "| Close:",
            candle["close"],
        )
else:
    print("UTC boundary response:", boundary.get("message", boundary))

# Diagnostic: inspect daily Gold OHLC values.
print("\n--- XAU/USD daily OHLC diagnostic ---")

for candle in raw["values"]:
    print(
        "Date:", candle["datetime"],
        "| Open:", candle["open"],
        "| High:", candle["high"],
        "| Low:", candle["low"],
        "| Close:", candle["close"],
    )

# Diagnostic: inspect hourly Gold candle timestamps.
print("\n--- XAU/USD hourly candle diagnostic ---")

hourly = get_json(
    "https://api.twelvedata.com/time_series",
    {
        "symbol": "XAU/USD",
        "interval": "1h",
        "outputsize": 72,
        "timezone": "UTC",
        "apikey": os.environ["PRICE_API_KEY"],
        "format": "JSON",
    },
)

if "values" in hourly:
    print("Hourly API metadata:", hourly.get("meta", {}))
    for candle in hourly["values"]:
        print(
            "Hourly candle:", candle["datetime"],
            "| Open:", candle["open"],
            "| Close:", candle["close"],
        )
else:
    print("Hourly API response:", hourly.get("message", hourly))
