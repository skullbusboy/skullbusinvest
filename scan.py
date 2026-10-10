"""Free SET + mai daily MACD scanner. Run: python scan.py
Data sources: TradingView public scanner for discovery (best effort), Yahoo chart for OHLCV.
No fictitious data: unavailable symbols are flagged. Unofficial endpoints can change.
"""
import csv
import datetime as dt
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'data'/'latest.json'
USER_AGENT='Mozilla/5.0 (compatible; ThaiMACDScanner/1.0)'
SESSION=requests.Session(); SESSION.headers.update({'User-Agent':USER_AGENT})


def discover():
    """TradingView symbols. Pagination avoids silently truncating large universes."""
    endpoint='https://scanner.tradingview.com/thailand/scan'
    found={}
    for start in range(0,5000,500):
        body={'filter':[{'left':'type','operation':'equal','right':'stock'}],
              'options':{'lang':'en'},'columns':['name','exchange','type'],
              'sort':{'sortBy':'name','sortOrder':'asc'},'range':[start,start+499]}
        resp=SESSION.post(endpoint,json=body,timeout=35);resp.raise_for_status()
        data=resp.json();rows=data.get('data',[])
        for row in rows:
            d=row.get('d',[]); symbol=str(d[0]).strip().upper() if d else ''
            exch=str(d[1]).upper() if len(d)>1 else ''
            if not symbol or not exch:continue
            # TradingView sometimes uses SET as exchange for both SET and mai;
            # market attribution is then UNKNOWN rather than invented.
            market='mai' if exch=='MAI' else 'SET' if exch=='SET' else None
            if market and all(c.isalnum() or c in '.-' for c in symbol):
                found[symbol]=market
        if len(rows)<500 or start+500>=data.get('totalCount',0):break
    if not found:raise RuntimeError('Discovery returned zero symbols')
    return found,'TradingView Thailand public scanner (market label best effort)'


def csv_universe():
    file=ROOT/'universe.csv'
    if not file.exists():return {},''
    with file.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    out={str(r['symbol']).strip().upper():str(r['market']).strip() for r in rows if r.get('symbol') and r.get('market') in ('SET','mai')}
    return out,'universe.csv'


def ema(values,period):
    alpha=2/(period+1); result=[];last=None
    for x in values:
        last=x if last is None else alpha*x+(1-alpha)*last
        result.append(last)
    return result


def calc(prices):
    if len(prices)<80:return None
    fast=ema(prices,12);slow=ema(prices,26)
    macd=[a-b for a,b in zip(fast,slow)]
    signal=ema(macd,9)
    return {'macd':round(macd[-1],6),'signal':round(signal[-1],6),
            'hist':round(macd[-1]-signal[-1],6),
            'crossed':macd[-2]<=0<macd[-1]}


def fetch_one(item):
    symbol,market=item
    record={'symbol':symbol,'market':market,'valid':False,'close':None,
            'macd':None,'signal':None,'hist':None,'crossed':False,'date':None,'reason':None}
    # Yahoo Thailand ticker suffix .BK. Some mai tickers might be unavailable.
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.BK'
    for attempt in range(3):
        try:
            resp=SESSION.get(url,params={'range':'1y','interval':'1d'},timeout=18)
            if resp.status_code in (429,500,502,503):time.sleep(1.5*(attempt+1));continue
            resp.raise_for_status();result=resp.json()['chart']['result'][0]
            quote=result['indicators']['quote'][0]['close']
            volumes=result['indicators']['quote'][0].get('volume',[])
            historical=[{'date':dt.datetime.fromtimestamp(ts,ZoneInfo('Asia/Bangkok')).date().isoformat(),'close':round(float(price),4),'volume':int(vol) if vol is not None else None} for ts,price,vol in zip(result['timestamp'],quote,volumes) if price is not None and math.isfinite(float(price)) and float(price)>0]
            pairs=[(ts,float(price)) for ts,price in zip(result['timestamp'],quote)
                   if price is not None and math.isfinite(float(price)) and float(price)>0]
            if len(pairs)<80:record['reason']=f'only {len(pairs)} daily closes';return record
            prices=[p for _,p in pairs];v=calc(prices)
            record.update(v);record['history']=historical[-260:];record.update(valid=True,close=round(prices[-1],4),
                          date=dt.datetime.fromtimestamp(pairs[-1][0],ZoneInfo('Asia/Bangkok')).date().isoformat())
            return record
        except Exception as e:
            record['reason']=str(e)[:140]
            if attempt<2:time.sleep(1+attempt)
    return record


def main():
    manual,manual_source=csv_universe()
    try:
        discovered,source=discover()
        # CSV overrides exchange classification for curated symbols.
        discovered.update(manual)
        if manual:source+=' + universe.csv overrides'
        universe=discovered
    except Exception as exc:
        if not manual:raise RuntimeError('Cannot discover universe and no fallback universe.csv') from exc
        universe,source=manual,manual_source+' (discovery unavailable; incomplete universe)'
        print('WARNING: discovery failed:',exc)
    print('Scanning',len(universe),'symbols from',source,flush=True)
    stocks=[]
    with ThreadPoolExecutor(max_workers=int(os.getenv('SCAN_WORKERS','6'))) as pool:
        futures={pool.submit(fetch_one,item):item[0] for item in universe.items()}
        for i,future in enumerate(as_completed(futures),1):
            try:stocks.append(future.result())
            except Exception as exc:print('ERROR',futures[future],exc)
            if i%100==0:print(i,'/',len(universe),flush=True)
    stocks.sort(key=lambda x:x['symbol'])
    dates=[s['date'] for s in stocks if s['valid']]
    latest=max(dates) if dates else None
    # Data from earlier sessions must not count as current signals.
    for s in stocks:
        if s['valid'] and s['date']!=latest:
            s['valid']=False;s['reason']='stale close (latest session: '+str(latest)+')'
    now=dt.datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(timespec='seconds')
    result={'generated_at':now,'latest_session':latest,'universe_source':source,
            'note':'Market labels and universe completeness depend on discovery source. Missing/stale data are excluded from valid counts. Not investment advice.',
            'stocks':stocks}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('Saved',OUT,'valid:',sum(s['valid'] for s in stocks),'positive:',sum(s['valid'] and s['macd']>0 for s in stocks))

if __name__=='__main__':main()
