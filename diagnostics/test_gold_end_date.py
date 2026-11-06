import datetime
import os
import requests

API = 'https://api.twelvedata.com/time_series'
KEY = os.environ["PRICE_API_KEY"]

today = datetime.datetime.now(datetime.timezone.utc).date()
cutoff = today - datetime.timedelta(days=1)

def fetch(end_date=None):
    params = {
        "symbol": "XAU/USD",
        "interval": "1day",
        "outputsize": 3,
        "timezone": "UTC",
        "apikey": KEY,
        "format": "JSON",
    }
    if end_date is not None:
        params["end_date"] = end_date

    response = requests.get(API, params=params, timeout=25)
    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        raise RuntimeError(data.get("message", "No candle data"))

    return data["values"]

print("Current UTC date:", today)
print("Requested cutoff:", cutoff)

latest = fetch()
restricted = fetch(cutoff.isoformat())

print("\nLatest daily candles:")
for candle in latest:
    print(candle["datetime"], "| Close:", candle["close"])

print("\nDate-restricted candles:")
for candle in restricted:
    print(candle["datetime"], "| Close:", candle["close"])

violations = [
    candle["datetime"]
    for candle in restricted
    if datetime.date.fromisoformat(candle["datetime"][:10]) > cutoff
]

if violations:
    print("\nFAIL: Candles returned beyond cutoff:", violations)
else:
    print("\nPASS: No candles returned beyond requested cutoff")

print("NOTE: This checks date filtering, not final candle settlement.")
