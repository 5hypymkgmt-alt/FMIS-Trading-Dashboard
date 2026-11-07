"""Check historical XAU/USD data availability on Twelve Data."""

import os
import requests

API = 'https://api.twelvedata.com/time_series'
KEY = os.environ.get('PRICE_API_KEY')

params = {
    "symbol": "XAU/USD",
    "interval": "1day",
    "outputsize": 1000,
    "timezone": "UTC",
    "apikey": KEY,
    "format": "JSON",
}

response = requests.get(API, params=params, timeout=30)
response.raise_for_status()
data = response.json()

if "values" not in data:
    raise RuntimeError(
        data.get("message", "No historical data returned")
    )

candles = data.get("values", [])
dates = sorted(c.get("datetime") for c in candles)

print("Market: XAU/USD")
print("Requested candles: 1000")
print("Returned candles:", len(candles))
print("Earliest date:", dates.__getitem__(0))
print("Latest date:", dates.__getitem__(-1))
print("Provider status:", data.get("status", "Not supplied"))
