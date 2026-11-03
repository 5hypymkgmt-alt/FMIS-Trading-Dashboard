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
