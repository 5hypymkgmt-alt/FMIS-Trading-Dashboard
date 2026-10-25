# FMIS daily market intelligence — deployable web app

Independent EdgeFinder-style research workflow. Not affiliated with A1 Trading.

## Quick start

1. Obtain a free FRED API key at https://fred.stlouisfed.org/docs/api/api_key.html and a compatible Twelve Data API key at https://twelvedata.com/. Check the provider's current free plan: symbols, exchanges, historical-bar limits, redistribution terms and rate limits **before** using it. Four daily symbols may not all be supported on free plans.
2. Create a GitHub repository, upload all files including `.github/workflows/daily.yml`, and enable GitHub Pages from branch `main` / root. GitHub Pages publishes `index.html` and `data.json`.
3. In repository Settings → Secrets and variables → Actions, add `FRED_API_KEY` and `PRICE_API_KEY`. Do not commit API keys to files.
4. Under Actions → Update FMIS daily → Run workflow, trigger a run. It writes `data.json` and commits it. Scheduled runs are best-effort, not guaranteed exactly on time.
5. Visit the GitHub Pages URL. If data is missing, inspect the workflow log and `data.json`. API failures show unavailable rather than fabricated values.
6. Paste `FMIS_Technical.pine` into TradingView Pine Editor, save, add to a **daily** chart and create alerts if desired.
7. Open `FMIS_Companion.xlsx` to log positioning, sentiment, setups and final approvals.

## What refreshes automatically

- **Daily prices and technicals**: Twelve Data `/time_series` API if configured and the plan supports each instrument. 20/50 EMAs, 14 RSI, 5-day momentum, and weekly 20 EMA context. Price proxies are SPY, GLD, QQQ and ISF.L. These are *not* identical to SPX, XAUUSD, NDX or FTSE100 cash indices. Gold GLD is an ETF proxy; its price is not XAUUSD.
- **Macro observations**: FRED DGS10, DGS2, T10YIE, UNRATE, CPIAUCSL, VIXCLS if configured. These series have different frequencies. The app shows values and observation dates, **not a falsely precise directional macro score**.
- **COT institutional positioning**: official source link, weekly/manual until an exact contract mapping and history/percentile pipeline is validated. Gold uses Disaggregated reports; equity index futures often use Traders in Financial Futures. Do not conflate trader categories.
- **Retail sentiment**: unavailable until a licensed, documented feed is connected. Broker-specific long/short percentages should not be assumed transferable to another broker.
- **Options gamma**: not included; reliable real-time SPX dealer gamma typically requires paid specialized feeds, and even paid gamma is model-estimated.

## Mechanical swing-trade checklist

A technical LONG candidate requires a confirmed daily close, score >= +4/5, price > EMA20, EMA20 > EMA50, and previous completed weekly close > previous completed weekly EMA20. Reverse for SHORT (<= -4/5). Technical signals are *candidates only*. The final decision is NO TRADE until you manually verify: macro and positioning source freshness, sentiment availability, reaction at pre-marked support/resistance/pivot, logical swing stop, target >= 2R, account risk <= 1% per trade, correlated exposure and scheduled high-impact releases. If required information is unavailable, skip the trade rather than score missing data as zero.

## Limitations / validation

- The app **does not claim live quotes**; daily bars can be delayed and data can be stale. A 5-calendar-day price freshness check handles typical weekends but not all holidays.
- The weekly context is approximated by ISO-week last closes and excludes the current week; Pine Script uses TradingView's exchange calendar and can differ around holidays.
- The updater stores the latest snapshot only. To backtest, build a point-in-time historical store with vintage macro releases and COT publication times; otherwise you risk lookahead bias.
- Static GitHub Pages sites publish data.json publicly. Do not include private information or API secrets in it.
- Use a provider and subscription permitting the intended use, including any public redistribution.
- If a provider rate-limits or rejects a symbol, the UI reports unavailable. The free price plan may not cover FTSE/LSE symbols; consider a paid data subscription if needed.
- Educational tool, not financial advice. Paper trade and validate performance before live use.
