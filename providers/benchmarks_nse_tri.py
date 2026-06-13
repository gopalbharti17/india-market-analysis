"""
providers/benchmarks_nse_tri.py — TOTAL RETURN INDEX (TRI) benchmark provider
from NSE's official index portal (niftyindices.com). Free.

WHY THIS EXISTS (the bug it fixes):
Mutual fund NAVs include reinvested dividends; ordinary "price" indices
(what Yahoo serves) do not. Comparing a fund to a price index therefore
overstates its alpha by roughly the index dividend yield (~1-1.5%/yr).
SEBI itself mandates that funds benchmark against TRI. This provider gives
the analysis the correct yardstick.

SAFETY DESIGN: the niftyindices endpoint is unofficial-ish and occasionally
moody. If a TRI fetch fails for any reason, this provider FALLS BACK to the
Yahoo price index and prints a loud warning that alpha will be overstated —
the system keeps running, and you always know which yardstick was used.
"""

import json
import datetime as dt

import pandas as pd
import requests

from providers.base import BenchmarkProvider
from providers.benchmarks_yahoo import YahooBenchmarkProvider
from core import cache

TRI_URL = "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString"

# Yahoo-style ticker (used throughout config) -> official NSE index name
TICKER_TO_NSE_NAME = {
    "^NSEI": "NIFTY 50",
    "^NSEMDCP50": "NIFTY MIDCAP 50",
    "^CNXSC": "NIFTY SMALLCAP 100",
    "^NSEBANK": "NIFTY BANK",
    "^CNXIT": "NIFTY IT",
}

HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.niftyindices.com/reports/historical-data",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


class NSETRIBenchmarkProvider(BenchmarkProvider):

    def __init__(self, years: int = 10):
        self.years = years
        self._fallback = YahooBenchmarkProvider()
        self._mem: dict[str, pd.Series] = {}

    def get_history(self, ticker: str, period: str = "10y") -> pd.Series | None:
        if ticker in self._mem:
            return self._mem[ticker]

        nse_name = TICKER_TO_NSE_NAME.get(ticker)
        if nse_name:
            try:
                series = self._fetch_tri(nse_name)
                if series is not None and len(series) > 250:
                    print(f"  benchmark {nse_name}: using official TRI data")
                    self._mem[ticker] = series
                    return series
            except Exception as e:
                print(f"  !! TRI fetch failed for {nse_name}: {e}")

        print(f"  !! WARNING: falling back to PRICE index for {ticker} — "
              f"fund alpha will be OVERSTATED by ~1-1.5%/yr vs this benchmark.")
        series = self._fallback.get_history(ticker, period)
        if series is not None:
            self._mem[ticker] = series
        return series

    # ---------- internals ----------

    def _fetch_tri(self, nse_name: str) -> pd.Series | None:
        cache_key = f"tri:{nse_name}:{self.years}y"
        cached = cache.get(cache_key, max_age_hours=24)
        if cached is not None:
            s = pd.Series(cached["values"],
                          index=pd.to_datetime(cached["dates"]))
            return s.sort_index()

        end = dt.date.today()
        start = end - dt.timedelta(days=int(self.years * 365.25))
        frames = []
        # the endpoint behaves best with ~1-year windows; chunk the range
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + dt.timedelta(days=364), end)
            frames.append(self._fetch_chunk(nse_name, chunk_start, chunk_end))
            chunk_start = chunk_end + dt.timedelta(days=1)

        df = pd.concat([f for f in frames if f is not None and not f.empty])
        if df.empty:
            return None
        df = df[~df.index.duplicated()].sort_index()

        cache.set(cache_key, {"dates": [d.isoformat() for d in df.index],
                              "values": df.tolist()})
        return df

    def _fetch_chunk(self, nse_name: str, start: dt.date, end: dt.date) -> pd.Series | None:
        cinfo = ("{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}"
                 % (nse_name, start.strftime("%d-%b-%Y"),
                    end.strftime("%d-%b-%Y"), nse_name))
        resp = requests.post(TRI_URL, headers=HEADERS,
                             data=json.dumps({"cinfo": cinfo}), timeout=30)
        resp.raise_for_status()
        rows = json.loads(resp.json().get("d", "[]"))
        if not rows:
            return None
        df = pd.DataFrame(rows)
        # response fields: 'Date' (e.g. '01 Jan 2020') and 'TotalReturnsIndex'
        date_col = next(c for c in df.columns if "date" in c.lower())
        val_col = next(c for c in df.columns if "totalreturn" in c.lower().replace(" ", ""))
        s = pd.Series(pd.to_numeric(df[val_col], errors="coerce").values,
                      index=pd.to_datetime(df[date_col], format="mixed", dayfirst=True))
        return s.dropna()
