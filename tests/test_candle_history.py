"""Test minimum history after excluding an incomplete candle."""

import datetime

MIN_BARS = 210

start = datetime.date(2026, 1, 1)

candles = [
    {
        "datetime": (start + datetime.timedelta(days=i)).isoformat(),
        "close": str(3900 + i),
    }
    for i in range(211)
]

cutoff = start + datetime.timedelta(days=210)

completed = [
    candle for candle in candles
    if datetime.date.fromisoformat(candle["datetime"]) < cutoff
]

assert len(completed) == MIN_BARS
print("PASS: 210 completed candles retained")

insufficient = completed[:-1]

assert len(insufficient) < MIN_BARS
print("PASS: Insufficient history detected")

print("Completed candles:", len(completed))
