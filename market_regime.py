"""FMIS Market Regime Detector — independent calculations."""

def calculate_adx(high, low, close, period=14):
    """Calculate ADX and directional indicators using Wilder smoothing."""
    if len(close) != len(high) or len(close) != len(low):
        return None
    if len(close) < 2 * period + 1:
        return None

    tr, plus_dm, minus_dm = [], [], []

    for i in range(1, len(close)):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]

        tr.append(max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        ))
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)

    def smooth(values):
        result = [sum(values[:period])]
        for value in values[period:]:
            result.append(result[-1] - result[-1] / period + value)
        return result

    atr = smooth(tr)
    pdm = smooth(plus_dm)
    mdm = smooth(minus_dm)

    dx = []
    for a, p, m in zip(atr, pdm, mdm):
        plus = 100 * p / a if a else 0
        minus = 100 * m / a if a else 0
        total = plus + minus
        dx.append(100 * abs(plus - minus) / total if total else 0)

    adx = sum(dx[:period]) / period
    for value in dx[period:]:
        adx = (adx * (period - 1) + value) / period

    return round(adx, 2)


def classify_market_regime(adx, direction=0):
    """Classify trend strength and direction."""

    if adx is None:
        return "Unavailable"

    if adx < 20:
        return "Ranging"

    if adx < 25:
        return "Transitional"

    if direction > 0:
        return "Strong Bullish Trend" if adx >= 40 else "Bullish Trend"

    if direction < 0:
        return "Strong Bearish Trend" if adx >= 40 else "Bearish Trend"

    return "Trend Direction Unclear"
