},
        'Nasdaq 100': {
            'DGS10': -1,
            'DGS2': -1,
            'T10YIE': 0,
            'UNRATE': -1,
            'VIXCLS': -1
        }
    }

    results = {}

    for market, indicators in weights.items():
        score = 0
        used = {}
        available = 0
        total = sum(1 for weight in indicators.values()
                    if weight != 0)

        for series, weight in indicators.items():
            if weight == 0:
                continue

            data = macro_data.get(series, {})

            if data.get('status') != 'ok':
                used[series] = None
                continue

            direction = data.get('direction')

            if direction == 'rising':
                points = weight
            elif direction == 'falling':
                points = -weight
            elif direction == 'unchanged':
                points = 0
            else:
                used[series] = None
                continue

            score += points
            available += 1
            used[series] = points

        if available == 0:
            bias = 'Insufficient data'
        elif available < total:
            bias = 'Incomplete data'
        elif score >= 2:
            bias = 'Bullish macro'
        elif score <= -2:
            bias = 'Bearish macro'
        else:
            bias = 'Mixed macro'

        results[market] = {
            'score': score,
            'maximum_score': total,
            'indicators_available': available,
            'indicators_required': total,
            'bias': bias,
            'factors': used,
            'note': 'Heuristic macro score, not a trade signal'
        }

    return results

def main():
    out={'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'markets':{},'macro':{},
         'positioning':{'status':'manual','source':'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
                        'note':'Weekly Tuesday positions typically published Friday. No automatic contract mapping configured.'},
         'sentiment':{'status':'unavailable','note':'No verified free retail sentiment feed connected. Do not infer sentiment from price.'},
         'rules':{'minimum_rr':2,'max_risk_percent':1,'long_technical':'all core trend gates + technical score >= 4/5',
                  'short_technical':'all core trend gates + technical score <= -4/5',
                  'final':'NO TRADE until macro, positioning, sentiment, level reaction, stop and event risk are verified'}}
    for name, cfg in CFG['markets'].items():
        print(f"Processing market: {name}, symbol: {cfg['symbol']}")
        try:
            p = prices(cfg['symbol'])
        except Exception as e:
            p = {'status': 'unavailable', 'reason': str(e)}
        out['markets'][name] = {**cfg, 'price': p}
    
    for series in CFG['macro_series']:
        try:
            out['macro'][series] = macro(series)
        except Exception as e:
            out['macro'][series] = {
                'status': 'unavailable',
                'reason': str(e)
            }
            

    out['macro_scores'] = macro_scores(out['macro'])

    (ROOT / 'data.json').write_text(
        json.dumps(out, indent=2)
    )

    print('Wrote data.json:', out['generated_at_utc'])


if __name__ == '__main__':
    main()
