import os
import json
import urllib.parse
import urllib.request
import urllib.error

key = os.getenv("PRICE_API_KEY", "")
if not key:
    raise SystemExit("PRICE_API_KEY is unavailable")

failures = 0

for name, symbol in [
    ("S&P 500 ETF", "SPY"),
    ("Nasdaq-100 ETF", "QQQ"),
    ("Gold Spot", "XAU/USD"),
]:
    params = urllib.parse.urlencode({
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 260,
        "apikey": key,
    })
    url = "https://api.twelvedata.com/time_series?" + params

    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            data = json.load(response)

        candles = data.get("values", [])
        meta = data.get("meta", {})
        print(name, "| Exchange timezone:", meta.get("exchange_timezone", "Not provided"))
        print(name, "| Latest API candle:", candles[0].get("datetime") if candles else "None")
        valid = sum(
            all(c.get(k) not in (None, "") for k in
                ("datetime", "open", "high", "low", "close"))
            for c in candles
        )

        if valid >= 210:
            result = "PASS"
        else:
            result = "INSUFFICIENT DATA"

        if data.get("status") == "error":
            result = "API ERROR"

        if result != "PASS":
            failures += 1

        print(name, "|", symbol, "|", result,
              "| Valid candles:", valid,
              "|", str(data.get("message", ""))[:160])

    except urllib.error.HTTPError as exc:
        failures += 1
        print(name, "| HTTP", exc.code, "|", exc.read().decode("utf-8", errors="replace")[:250])
    except Exception as exc:
        failures += 1
        print(name, "| REQUEST FAILED |", type(exc).__name__)

if failures:
    raise SystemExit(f"FAIL: {failures} underlying market price check(s) failed")

print("PASS: All underlying market price checks succeeded")
