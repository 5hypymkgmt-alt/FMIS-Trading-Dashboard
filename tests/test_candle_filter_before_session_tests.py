"""Independent FMIS daily candle-filter tests."""

import datetime

def filter_completed_candles(candles, cutoff_date):
    """Keep candles dated before the supplied cutoff date."""
    return [
        candle for candle in candles
        if datetime.date.fromisoformat(
            candle["datetime"][:10]
        ) < cutoff_date
    ]

test_candles = [
    {"datetime": "2026-11-02", "close": "3944.31"},
    {"datetime": "2026-11-03", "close": "4000.00"},
    {"datetime": "2026-11-04", "close": "4048.59"},
]

cutoff = datetime.date(2026, 11, 4)

result = filter_completed_candles(test_candles, cutoff)

assert len(result) == 2
assert result[-1]["datetime"] == "2026-11-03"

print("PASS: Current UTC date excluded")
print("Latest retained candle:", result[-1]["datetime"])

# Test weekend and missing-session handling.
weekend_candles = [
    {"datetime": "2026-10-30", "close": "3900.00"},
    {"datetime": "2026-11-02", "close": "3944.31"},
    {"datetime": "2026-11-04", "close": "4048.59"},
]

weekend_result = filter_completed_candles(
    weekend_candles,
    datetime.date(2026, 11, 2),
)

assert len(weekend_result) == 1
assert weekend_result[-1]["datetime"] == "2026-10-30"

print("PASS: Missing weekend sessions handled")
print("Latest retained weekend-test candle:", weekend_result[-1]["datetime"])

# Test preservation of weekend-dated API records.
api_candles = [
    {"datetime": "2026-10-30", "close": "3900.00"},
    {"datetime": "2026-10-31", "close": "3875.44"},
    {"datetime": "2026-11-01", "close": "3875.43"},
    {"datetime": "2026-11-02", "close": "3944.31"},
]

api_result = filter_completed_candles(
    api_candles,
    datetime.date(2026, 11, 3),
)

assert len(api_result) == 4
assert api_result[-1]["datetime"] == "2026-11-02"

print("PASS: Weekend-dated API records preserved")
