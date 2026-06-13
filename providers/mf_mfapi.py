"""
providers/mf_mfapi.py — FREE mutual fund provider (AMFI data via mfapi.in),
with caching (NAVs only change once a day — never fetch twice).
"""

import requests
import pandas as pd

from providers.base import MFDataProvider
from core import cache

BASE_URL = "https://api.mfapi.in/mf/{code}"


class MFApiProvider(MFDataProvider):

    def get_nav_history(self, scheme_code: str) -> pd.DataFrame:
        payload = cache.get(f"mf:mfapi:{scheme_code}", max_age_hours=20)
        if payload is None:
            resp = requests.get(BASE_URL.format(code=scheme_code), timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            cache.set(f"mf:mfapi:{scheme_code}", payload)

        df = pd.DataFrame(payload["data"])
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df = df.dropna().sort_values("date").reset_index(drop=True)

        meta = payload.get("meta", {})
        df.attrs["scheme_name"] = meta.get("scheme_name", scheme_code)
        df.attrs["category"] = meta.get("scheme_category", "")
        df.attrs["fund_house"] = meta.get("fund_house", "")
        return df
