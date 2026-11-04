"""Consolidated FMIS price-feed diagnostic for SPY, XAU/USD and QQQ."""

import datetime
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import update

MARKETS = [
    ("S&P 500 ETF", "SPY"),
    ("Gold Spot", "XAU/USD"),
    ("Nasdaq-100 ETF", "QQQ"),
]

print("FMIS consolidated price diagnostic")
print("UTC time:", datetime.datetime.now(datetime.timezone.utc).isoformat())
print("Configured markets:", ", ".join(symbol for _, symbol in MARKETS))

API_KEY = os.getenv("PRICE_API_KEY", "")

if not API_KEY:
    raise SystemExit(
        "PRICE_API_KEY is unavailable. "
        "No Twelve Data requests were made."
    )

print("Twelve Data API key: configured")

def fetch_market_data(symbol):
    """Retrieve one Twelve Data response for a market."""
    data = update.get_json(
        "https://api.twelvedata.com/time_series",
        {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": 260,
            "apikey": API_KEY,
            "format": "JSON",
        },
    )

    if not isinstance(data, dict):
        raise RuntimeError(f"{symbol}: invalid API response")

    if data.get("status") == "error":
        raise RuntimeError(
            f"{symbol}: {data.get('message', 'Unknown API error')}"
        )

    candles = data.get("values")

    if not isinstance(candles, list) or not candles:
        raise RuntimeError(f"{symbol}: no daily candles returned")

    return data

def validate_candle_history(symbol, data):
    """Validate completed daily candle history and report metadata."""
    candles = data["values"]
    meta = data.get("meta") or {}

    if not isinstance(meta, dict):
        meta = {}

    latest_api_date = max(c["datetime"] for c in candles)

    completed = update.filter_completed_daily_candles(
        candles,
        datetime.datetime.now(datetime.timezone.utc).date()
    )

    print(symbol, "| Exchange timezone:",
          meta.get("exchange_timezone", "Not provided"))
    print(symbol, "| Latest API candle:", latest_api_date)
    print(symbol, "| Completed candles:", len(completed))

    if len(completed) < 210:
        raise RuntimeError(
            f"{symbol}: fewer than 210 completed daily candles"
        )

    print(symbol, "| Candle history: PASS")
    return completed

def validate_fmis_calculations(symbol, data):
    """Test FMIS calculations using an already downloaded API response."""
    with patch.dict(os.environ, {"PRICE_API_KEY": "cached-test"}):
        with patch.object(update, "get_json", return_value=data):
            result = update.prices(symbol)

    if result.get("status") != "ok":
        raise RuntimeError(
            f"{symbol}: FMIS calculation failed: "
            f"{result.get('reason', result)}"
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

    import math

    for field in fields:
        value = result.get(field)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise RuntimeError(
                f"{symbol}: invalid FMIS indicator: {field}"
            )

    print(symbol, "| FMIS calculations: PASS")
    print(symbol, "| FMIS candle date:", result.get("date"))
    print(symbol, "| FMIS closing price:", result.get("close"))

    return result

def main():
    failures = []

    for name, symbol in MARKETS:
        print("\n---", name, "|", symbol, "---")

        try:
            data = fetch_market_data(symbol)
            validate_candle_history(symbol, data)
            validate_fmis_calculations(symbol, data)
            print(symbol, "| Overall result: PASS")

        except Exception as exc:
            failures.append(symbol)
            print(symbol, "| Overall result: FAIL")
            print(symbol, "| Reason:", str(exc)[:300])

    if failures:
        raise SystemExit(
            "FAIL: Price diagnostics failed for "
            + ", ".join(failures)
        )

    print("\nPASS: All three FMIS market diagnostics succeeded")


if __name__ == "__main__":
    main()
