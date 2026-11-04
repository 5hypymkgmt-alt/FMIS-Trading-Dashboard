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

assert result.get("status") == "ok", (
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
