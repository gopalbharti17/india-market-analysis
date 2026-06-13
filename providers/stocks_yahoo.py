"""
providers/stocks_yahoo.py — FREE stock provider (Yahoo Finance), with caching.
"""

import yfinance as yf
import pandas as pd

from providers.base import StockDataProvider
from core.schemas import conform_stock_row
from core import cache


class YahooStockProvider(StockDataProvider):

    def get_stock(self, ticker: str) -> dict:
        cached = cache.get(f"stock:yahoo:{ticker}", max_age_hours=12)
        if cached is not None:
            return cached

        stock = yf.Ticker(ticker)
        info = stock.info or {}
        hist = stock.history(period="1y")

        six_month_return = pct_from_52w_high = above_200dma = None
        if not hist.empty and len(hist) > 20:
            close = hist["Close"]
            if len(close) >= 126:
                six_month_return = (close.iloc[-1] / close.iloc[-126] - 1) * 100
            pct_from_52w_high = (close.iloc[-1] / close.max() - 1) * 100
            if len(close) >= 200:
                above_200dma = bool(close.iloc[-1] > close.rolling(200).mean().iloc[-1])

        row = conform_stock_row({
            "ticker": ticker,
            "name": info.get("shortName"),
            "sector": info.get("sector"),
            "market_cap_cr": (info.get("marketCap") or 0) / 1e7 or None,
            "price": info.get("currentPrice"),
            "roe": _pct(info.get("returnOnEquity")),
            "roa": _pct(info.get("returnOnAssets")),
            "profit_margin": _pct(info.get("profitMargins")),
            "debt_to_equity": info.get("debtToEquity"),
            "earnings_growth": _pct(info.get("earningsGrowth")),
            "revenue_growth": _pct(info.get("revenueGrowth")),
            "pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "six_month_return": six_month_return,
            "pct_from_52w_high": pct_from_52w_high,
            "above_200dma": above_200dma,
        })
        cache.set(f"stock:yahoo:{ticker}", row)
        return row


def _pct(x):
    return round(x * 100, 2) if isinstance(x, (int, float)) else None
