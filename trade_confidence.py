def trade_confidence(name, market, direction, data):
    p = market.get("price", {})
    macro = data.get("macro", {})

    if p.get("status") != "ok":
        return {"status": "Unavailable", "reason": "Price data unavailable"}
    price_age = p.get("age_days")
    if not isinstance(price_age, (int, float)) or price_age < 0 or price_age > 5:
        return {"status": "Unavailable", "reason": "Stale price data"}

    technical = p.get("technical_score")
    adx = p.get("adx14")
    regime = p.get("market_regime")
    structure = p.get("market_structure", {})
    valid_regimes = ("Ranging", "Transitional", "Bullish Trend", "Bearish Trend", "Strong Bullish Trend", "Strong Bearish Trend")
    if regime not in valid_regimes:
        return {"status": "Unavailable", "reason": "Market regime missing or invalid"}

    if not isinstance(technical, (int, float)):
        return {"status": "Unavailable"}

    if not isinstance(adx, (int, float)):
        return {"status": "Unavailable"}

    if direction not in ("Bullish", "Bearish"):
        raise ValueError("Invalid direction")
    sign = 1 if direction == "Bullish" else -1
    factors = p.get("factors", {})
    factor_names = ("price_vs_ema20", "ema20_vs_ema50", "weekly_trend", "momentum_5d", "rsi_14")
    if not isinstance(factors, dict) or any(factors.get(k) not in (-1, 0, 1) for k in factor_names):
        return {"status": "Unavailable", "reason": "Technical factors incomplete"}
    technical_points = sum(6 for k in factor_names if factors[k] == sign)

    # Trend strength: maximum 25 points
    if regime == "Ranging":
        trend_points = 0
    elif regime == "Transitional":
        trend_points = 0
    elif "Trend" in str(regime):
        aligned = direction in regime
        trend_points = (25 if adx >= 25 else 10) if aligned else 0
    else:
        trend_points = 0

    # Macro alignment: maximum 25 points
    macro_keys = (
        ("DGS10", "VIXCLS") if name != "Gold"
        else ("DFII10", "DTWEXBGS")
    )

    macro_points = 0
    macro_excluded = []
    for key in macro_keys:
        item = macro.get(key, {})
        age = item.get("age_days")
        movement = item.get("direction")
        if item.get("status") != "ok" or movement not in ("rising", "falling"):
            macro_excluded.append(key)
            continue
        if not isinstance(age, (int, float)) or age < 0 or age > 5:
            macro_excluded.append(key)
            continue
        supports_bullish = movement == "falling"
        if supports_bullish == (sign == 1):
            macro_points += 12.5

    # Market structure: maximum 20 points
    if not isinstance(structure, dict) or structure.get("trend") not in ("Bullish", "Bearish", "Ranging / Mixed"):
        return {"status": "Unavailable", "reason": "Market structure missing or invalid"}
    structure_trend = structure.get("trend")
    choch = structure.get("choch", "None")
    opposing_choch = (direction == "Bullish" and choch == "Bearish CHoCH") or (direction == "Bearish" and choch == "Bullish CHoCH")
    structure_points = (10 if opposing_choch else 20) if structure_trend == direction else 0

    confidence = max(0, min(100, round(
        technical_points + trend_points +
        macro_points + structure_points
    )))

    return {
        "direction": direction,
        "status": "Partial Data" if macro_excluded else "Complete",
        "excluded_macro": macro_excluded,
        "confidence": confidence,
        "technical": technical_points,
        "trend": trend_points,
        "macro": macro_points,
        "structure": structure_points
    }

