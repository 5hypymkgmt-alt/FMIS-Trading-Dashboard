import os
import json
import urllib.parse
import urllib.request
import urllib.error

key = os.getenv("PRICE_API_KEY", "")
if not key:
    raise SystemExit("PRICE_API_KEY is unavailable")

for name, symbol in [
    ("S&P 500", "SPX"),
    ("Nasdaq-100", "NDX"),
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

        print(name, "|", symbol, "|", result,
              "| Valid candles:", valid,
              "|", str(data.get("message", ""))[:160])

    except urllib.error.HTTPError as exc:
        print(name, "| HTTP", exc.code, "|", exc.read().decode("utf-8", errors="replace")[:250])
    except Exception as exc:
        print(name, "| REQUEST FAILED |", type(exc).__name__)
