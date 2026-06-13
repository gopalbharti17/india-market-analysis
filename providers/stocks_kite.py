"""
providers/stocks_kite.py — PAID provider stub: Zerodha Kite Connect.
NOT ACTIVE until you subscribe (~Rs 2000/month) and fill in the TODOs.

This file exists now so you can see how cheap the future upgrade is:
implement get_stock() to return the same canonical dict, flip one line
in config.py (STOCK_PROVIDER = "kite"), and the entire system — screener,
agent, reports — runs on professional-grade data with zero other changes.

Setup when ready:
  1. pip install kiteconnect
  2. Create an app at https://developers.kite.trade -> get api_key/secret
  3. Put credentials in environment variables (NEVER hard-code keys):
       export KITE_API_KEY=...
       export KITE_ACCESS_TOKEN=...
  4. Note: Kite gives superb PRICE data; for fundamentals you'd pair it
     with another source (or keep Yahoo for fundamentals and Kite for
     prices — providers can be mixed because each is independent).
"""

import os
from providers.base import StockDataProvider
from core.schemas import conform_stock_row


class KiteStockProvider(StockDataProvider):

    def __init__(self):
        api_key = os.environ.get("KITE_API_KEY")
        access_token = os.environ.get("KITE_ACCESS_TOKEN")
        if not (api_key and access_token):
            raise RuntimeError(
                "Kite credentials missing. Set KITE_API_KEY and KITE_ACCESS_TOKEN "
                "environment variables (see file header for setup steps)."
            )
        # TODO when subscribed:
        # from kiteconnect import KiteConnect
        # self.kite = KiteConnect(api_key=api_key)
        # self.kite.set_access_token(access_token)
        raise NotImplementedError("Fill in the TODOs after subscribing to Kite Connect.")

    def get_stock(self, ticker: str) -> dict:
        # TODO: map ticker -> Kite instrument token, fetch quote + historical
        # candles, compute the same momentum fields, and return:
        # return conform_stock_row({...})
        raise NotImplementedError
