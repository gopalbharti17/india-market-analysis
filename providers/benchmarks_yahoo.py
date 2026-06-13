"""
providers/benchmarks_yahoo.py — FREE benchmark index provider (Yahoo), cached.
"""

import yfinance as yf
import pandas as pd

from providers.base import BenchmarkProvider
from config import CATEGORY_BENCHMARKS, DEFAULT_BENCHMARK


def benchmark_for_category(category: str) -> str:
    cat = (category or "").lower()
    for keyword, ticker in CATEGORY_BENCHMARKS:
        if keyword in cat:
            return ticker
    return DEFAULT_BENCHMARK


class YahooBenchmarkProvider(BenchmarkProvider):

    def __init__(self):
        self._mem: dict[str, pd.Series] = {}  # per-run memory cache

    def get_history(self, ticker: str, period: str = "10y") -> pd.Series | None:
        if ticker in self._mem:
            return self._mem[ticker]
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if hist.empty:
                print(f"  !! no data for benchmark {ticker}")
                return None
            series = hist["Close"]
            series.index = series.index.tz_localize(None)
            self._mem[ticker] = series
            return series
        except Exception as e:
            print(f"  !! benchmark fetch failed for {ticker}: {e}")
            return None
