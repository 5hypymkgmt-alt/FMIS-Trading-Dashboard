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

def prices(symbol):
    key=os.getenv('PRICE_API_KEY','')
    if not key:return {'status':'unavailable','reason':'PRICE_API_KEY not configured; no automated price feed'}
    j=get_json('https://api.twelvedata.com/time_series',{'symbol':symbol,'interval':'1day','outputsize':260,'apikey':key,'format':'JSON'})
    if j.get('status')=='error' or 'values' not in j: return {'status':'unavailable','reason':j.get('message','No price history returned')}
    vals=sorted(j['values'],key=lambda x:x['datetime'])
    try:
        dates=[x['datetime'][:10] for x in vals];close=[float(x['close']) for x in vals]
        if len(close)<210:raise ValueError('At least 210 daily bars required')
        last=close[-1];e20=ema(close,20);e50=ema(close,50)
        # Weekly trend proxy uses Friday-or-last trading day close per ISO week; excludes incomplete current week.
        groups={}
        for d,c in zip(dates,close):
            dt=datetime.date.fromisoformat(d);groups[(dt.isocalendar().year,dt.isocalendar().week)]=c
        w=list(groups.values())[:-1]
        if len(w)<21:raise ValueError('At least 21 completed weekly bars required')
        ew=ema(w,20)
        factors={'price_vs_ema20':1 if last>e20 else -1 if last<e20 else 0,
                 'ema20_vs_ema50':1 if e20>e50 else -1 if e20<e50 else 0,
                 'weekly_trend':1 if w[-1]>ew else -1 if w[-1]<ew else 0,
                 'momentum_5d':1 if last>close[-6] else -1 if last<close[-6] else 0,
                 'rsi_14':1 if rsi(close)>55 else -1 if rsi(close)<45 else 0}
        age=(TODAY-datetime.date.fromisoformat(dates[-1])).days
        return {'status':'ok' if age<=CFG['max_price_age_days'] else 'stale','date':dates[-1], 'age_days':age,
                'close':round(last,3),'ema20':round(e20,3),'ema50':round(e50,3),'rsi14':round(rsi(close),2),
                'factors':factors,'technical_score':sum(factors.values()),'technical_max':len(factors),
                'source':'https://twelvedata.com/','feed':'Twelve Data daily API; plan/exchange delays may apply'}
    except (ValueError,KeyError,IndexError,TypeError) as e:return {'status':'unavailable','reason':str(e)}

def macro(series):
    key=os.getenv('FRED_API_KEY','')
    if not key:return {'status':'unavailable','reason':'FRED_API_KEY not configured'}
    try:
        
    params = {
        'symbol': symbol,
        'interval': '1day',
        'outputsize': 260,
        'apikey': key,
        'format': 'JSON'
    }

    # Specify London Stock Exchange for the FTSE 100 ETF.
    if symbol == 'ISF':
        params['exchange'] = 'LSE'

    response = S.get(
        'https://api.twelvedata.com/time_series',
        params=params,
        timeout=25
    )

    try:
        j = response.json()
    except ValueError:
        return {
            'status': 'unavailable',
            'reason': f'Non-JSON API response (HTTP {response.status_code})'
        }

    if response.status_code >= 400:
        return {
            'status': 'unavailable',
            'reason': (
                f"HTTP {response.status_code}: "
                f"{j.get('message', 'API request failed')}"
            )
        }

        observations=[x for x in j['observations'] if x['value']!='.']
        if not observations:raise ValueError('No numeric observations')
        latest=observations[0];age=(TODAY-datetime.date.fromisoformat(latest['date'])).days
        return {'status':'ok' if age<=CFG['max_macro_age_days'] else 'stale','value':float(latest['value']),
                'observation_date':latest['date'],'age_days':age,'source':'https://fred.stlouisfed.org/series/'+series,
                'caveat':'Observation date is not publication timestamp; revisions possible'}
    except (ValueError,KeyError,requests.RequestException) as e:return {'status':'unavailable','reason':str(e)}

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
        try:out['macro'][series]=macro(series)
        except Exception as e:out['macro'][series]={'status':'unavailable','reason':str(e)}
    (ROOT/'data.json').write_text(json.dumps(out,indent=2))
    print('Wrote data.json:',out['generated_at_utc'])
if __name__=='__main__':main()
