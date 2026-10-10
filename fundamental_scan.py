"""Best-effort SET/mai fundamental snapshot from TradingView public scanner.
Run: python fundamental_scan.py
Unofficial source: fields/availability may change. Missing values remain null.
"""
import datetime as dt
import json
import math
import time
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'fundamentals.json'
ENDPOINT = 'https://scanner.tradingview.com/thailand/scan'
COLUMNS = ['name', 'exchange', 'price_earnings_ttm', 'dividends_yield_current',
           'market_cap_basic', 'net_income_ttm']


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def main():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    stocks = {}
    total = None
    for start in range(0, 5000, 250):
        body = {'filter': [{'left': 'type', 'operation': 'equal', 'right': 'stock'}],
                'options': {'lang': 'en'}, 'columns': COLUMNS,
                'sort': {'sortBy': 'name', 'sortOrder': 'asc'},
                'range': [start, start + 249]}
        response = None
        for attempt in range(3):
            try:
                response = session.post(ENDPOINT, json=body, timeout=35)
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        payload = response.json()
        rows = payload.get('data', [])
        total = payload.get('totalCount', total)
        for row in rows:
            values = row.get('d', [])
            if len(values) < len(COLUMNS):
                continue
            symbol = str(values[0] or '').strip().upper()
            exchange = str(values[1] or '').strip().upper()
            if exchange not in ('SET', 'MAI') or not symbol or not all(c.isalnum() or c in '.-' for c in symbol):
                continue
            pe = number(values[2])
            dividend = number(values[3])
            cap = number(values[4])
            profit = number(values[5])
            # TradingView dividend yield scanner field is expressed in percent.
            # Market capitalization and TTM income are nominal THB, convert to millions.
            if not any(v is not None for v in (pe, dividend, cap, profit)):
                continue
            stocks[symbol] = {
                'symbol': symbol, 'market': 'mai' if exchange == 'MAI' else 'SET',
                'pe': pe if pe is not None and pe > 0 else None,
                'dividend_yield_pct': dividend if dividend is not None and dividend >= 0 else None,
                'market_cap_mthb': round(cap / 1_000_000, 3) if cap is not None and cap > 0 else None,
                'net_profit_ttm_mthb': round(profit / 1_000_000, 3) if profit is not None else None,
                'as_of': dt.datetime.now(ZoneInfo('Asia/Bangkok')).date().isoformat(),
            }
        if not rows or len(rows) < 250 or (total is not None and start + len(rows) >= total):
            break
    if not stocks:
        raise RuntimeError('No usable fundamental rows returned; existing file left untouched')
    now = dt.datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(timespec='seconds')
    result = {
        'generated_at': now,
        'source': 'TradingView Thailand public scanner (unofficial; best effort)',
        'note': 'Snapshot as_of is retrieval date, not financial statement period. Verify reporting dates and units against SET filings before investment use. Coverage incomplete; missing values are null.',
        'stocks': sorted(stocks.values(), key=lambda s: s['symbol']),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'Saved {len(stocks)} fundamental records to {OUT}')


if __name__ == '__main__':
    main()
