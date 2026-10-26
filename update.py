"""Daily FMIS data updater. Requires FRED_API_KEY for macro; optional PRICE_API_KEY (Twelve Data)."""
import os, json, csv, io, math, datetime, pathlib, requests
ROOT=pathlib.Path(__file__).parent
CFG=json.loads((ROOT/'config.json').read_text())
TODAY=datetime.datetime.now(datetime.timezone.utc).date()
S=requests.Session(); S.headers['User-Agent']='FMIS-personal-research/1.0'

def get_json(url,params):
    r=S.get(url,params=params,timeout=25);r.raise_for_status();return r.json()

def ema(seq,n):
    k=2/(n+1);x=seq[0]
    for v in seq[1:]: x=v*k+x*(1-k)
    return x

def rsi(closes,n=14):
    if len(closes)<n+2:return None
    diffs=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains=[max(d,0) for d in diffs];losses=[max(-d,0) for d in diffs]
    g=sum(gains[:n])/n;l=sum(losses[:n])/n
    for i in range(n,len(diffs)):
        g=(g*(n-1)+gains[i])/n;l=(l*(n-1)+losses[i])/n
    return 100 if l==0 else 100-100/(1+g/l)

def market_structure(high, low, close, dates, strength=5):
    swing_highs = []
    swing_lows = []

    for i in range(strength, len(close) - strength):
        if high[i] > max(high[i-strength:i]) and \
           high[i] > max(high[i+1:i+strength+1]):
            swing_highs.append((i, high[i]))

        if low[i] < min(low[i-strength:i]) and \
           low[i] < min(low[i+1:i+strength+1]):
            swing_lows.append((i, low[i]))

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {'trend': 'Insufficient structure'}

    h1, h2 = swing_highs[-2], swing_highs[-1]
    l1, l2 = swing_lows[-2], swing_lows[-1]

    if h2[1] > h1[1] and l2[1] > l1[1]:
        trend = 'Bullish'
    elif h2[1] < h1[1] and l2[1] < l1[1]:
        trend = 'Bearish'
    else:
        trend = 'Ranging / Mixed'

    bos = 'None'

    if close[-1] > h2[1] and close[-2] <= h2[1]:
        bos = 'Bullish BOS'
    elif close[-1] < l2[1] and close[-2] >= l2[1]:
        bos = 'Bearish BOS'

    return {
        'trend': trend,
        'last_swing_high': round(h2[1], 3),
        'last_swing_low': round(l2[1], 3),
        'swing_high_date': dates[h2[0]],
        'swing_low_date': dates[l2[0]],
        'bos': bos
    }
def prices(symbol):
    key = os.getenv('PRICE_API_KEY', '')
    if not key:
        return {
            'status': 'unavailable',
            'reason': 'PRICE_API_KEY not configured'
        }

    j = get_json(
        'https://api.twelvedata.com/time_series',
        {
            'symbol': symbol,
            'interval': '1day',
            'outputsize': 260,
            'apikey': key,
            'format': 'JSON'
        }
    )

    if j.get('status') == 'error' or 'values' not in j:
        return {
            'status': 'unavailable',
            'reason': j.get('message', 'No price history returned')
        }

    vals = sorted(j['values'], key=lambda x: x['datetime'])

    try:
        
dates = [x['datetime'][:10] for x in vals]
open_prices = [float(x['open']) for x in vals]
close = [float(x['close']) for x in vals]
high = [float(x['high']) for x in vals]
low = [float(x['low']) for x in vals]


        if len(close) < 210:
            raise ValueError('At least 210 daily bars required')

        last = close[-1]
        e20 = ema(close, 20)
        e50 = ema(close, 50)
        structure = market_structure(high, low, close, dates)

        groups = {}
        for d, c in zip(dates, close):
            dt = datetime.date.fromisoformat(d)
            week = (dt.isocalendar().year, dt.isocalendar().week)
            groups[week] = c

        w = list(groups.values())[:-1]

        if len(w) < 21:
            raise ValueError('At least 21 completed weekly bars required')

        ew = ema(w, 20)
        current_rsi = rsi(close)

        factors = {
            'price_vs_ema20': 1 if last > e20 else -1 if last < e20 else 0,
            'ema20_vs_ema50': 1 if e20 > e50 else -1 if e20 < e50 else 0,
            'weekly_trend': 1 if w[-1] > ew else -1 if w[-1] < ew else 0,
            'momentum_5d': 1 if last > close[-6] else -1 if last < close[-6] else 0,
            'rsi_14': 1 if current_rsi > 55 else -1 if current_rsi < 45 else 0
        }

        age = (TODAY - datetime.date.fromisoformat(dates[-1])).days

        return {
            'status': 'ok' if age <= CFG['max_price_age_days'] else 'stale',
            'date': dates[-1],
            'age_days': age,
            'close': round(last, 3),
            'ema20': round(e20, 3),
            'ema50': round(e50, 3),
            'rsi14': round(current_rsi, 2),
            'factors': factors,
            'technical_score': sum(factors.values()),
            'technical_max': len(factors),
            'market_structure': structure,
            'source': 'https://twelvedata.com/',
            'feed': 'Twelve Data daily API; plan/exchange delays may apply'
        }

    except (ValueError, KeyError, IndexError, TypeError) as e:
        return {
            'status': 'unavailable',
            'reason': str(e)
        }





def macro(series):
    key = os.getenv('FRED_API_KEY', '')
    if not key:
        return {'status': 'unavailable',
                'reason': 'FRED_API_KEY not configured'}

    try:
        j = get_json(
            'https://api.stlouisfed.org/fred/series/observations',
            {
                'series_id': series,
                'api_key': key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 60
            }
        )

        obs = [
            x for x in j['observations']
            if x['value'] != '.'
        ]

        if len(obs) < 2:
            raise ValueError('Insufficient observations')

        latest = obs[0]
        
        previous = obs[min(20 if series in ('DFII10', 'DTWEXBGS') else 5, len(obs) - 1)]


        value = float(latest['value'])
        previous_value = float(previous['value'])
        change = value - previous_value

        age = (
            TODAY - datetime.date.fromisoformat(latest['date'])
        ).days

        # Monthly data has a longer acceptable age.
        max_age = 75 if series in (
            'UNRATE', 'CPIAUCSL'
        ) else 10

        return {
            'status': 'ok' if age <= max_age else 'stale',
            'value': value,
            'previous_value': previous_value,
            'change': round(change, 4),
            'direction': (
                'rising' if change > 0
                else 'falling' if change < 0
                else 'unchanged'
            ),
            'observation_date': latest['date'],
            'comparison_date': previous['date'],
            'age_days': age,
            'source': 'https://fred.stlouisfed.org/series/' + series,
            'caveat': 'Observation dates are not release dates; revisions possible'
        }

    except (ValueError, KeyError, TypeError,
            requests.RequestException) as e:
        return {
            'status': 'unavailable',
            'reason': str(e)
        }



def macro_scores(macro_data):
    # Directional research assumptions, not trading signals.
    # +1 means a rising indicator is favourable.
    # -1 means a falling indicator is favourable.
    #  0 means the relationship is too ambiguous to score.

    weights = {
        'Gold': {
            'DGS10': -1,
            'DGS2': -1,
            'T10YIE': 1,
            'UNRATE': 0,
            'VIXCLS': 0
        },
        'S&P 500': {
            'DGS10': -1,
            'DGS2': -1,
            'T10YIE': 0,
            'UNRATE': -1,
            'VIXCLS': -1
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
    for name,cfg in CFG['markets'].items():
        try:p=prices(cfg['symbol'])
        except Exception as e:p={'status':'unavailable','reason':str(e)}
        out['markets'][name]={**cfg,'price':p}
    
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

    
