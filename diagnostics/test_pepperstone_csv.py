"""Validate Pepperstone XAUUSD daily candles exported from TradingView."""

import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CSV_PATH = (
    Path.home()
    / "Downloads"
    / "PEPPERSTONESB_XAUUSD, 1D.csv"
)

NEW_YORK = ZoneInfo("America/New_York")


def load_pepperstone_candles(path):
    candles = []

    with path.open(newline="") as file:
        reader = csv.DictReader(file)

        expected = ["time", "open", "high", "low", "close"]
        if reader.fieldnames != expected:
            raise ValueError(f"Unexpected CSV columns: {reader.fieldnames}")

        for row in reader:
            utc = datetime.fromtimestamp(
                int(row["time"]), timezone.utc
            )
            local = utc.astimezone(NEW_YORK)

            if local.hour != 18 or local.minute != 0:
                raise ValueError(f"Unexpected session time: {local}")

            trading_date = (local + timedelta(days=1)).date()

            candle = {
                "date": trading_date.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }

            values = [
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
            ]

            if not all(math.isfinite(v) and v > 0 for v in values):
                raise ValueError(f"Invalid price: {candle}")

            if candle["high"] < max(candle["open"], candle["close"]):
                raise ValueError(f"Invalid high: {candle}")

            if candle["low"] > min(candle["open"], candle["close"]):
                raise ValueError(f"Invalid low: {candle}")

            candles.append(candle)

    dates = [c["date"] for c in candles]

    if dates != sorted(set(dates)):
        raise ValueError("Duplicate or unordered trading dates")

    return candles


if __name__ == "__main__":
    candles = load_pepperstone_candles(CSV_PATH)

    print("PASS: Pepperstone CSV validated")
    print("Total candles:", len(candles))
    print("First trading date:", candles[0]["date"])
    print("Last trading date:", candles[-1]["date"])
    print("First candle:", candles[0])
    print("Last candle:", candles[-1])
