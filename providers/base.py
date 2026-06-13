"""
providers/base.py — The interfaces every data provider must implement.

To add ANY new data source (paid or free), subclass one of these,
implement its methods returning canonical-schema data, then register it
in providers/registry.py. That's the whole job.
"""

from abc import ABC, abstractmethod
import pandas as pd


class StockDataProvider(ABC):
    """Supplies stock fundamentals + momentum snapshots."""

    @abstractmethod
    def get_stock(self, ticker: str) -> dict:
        """One stock -> dict matching core.schemas.STOCK_SCHEMA."""

    def get_many(self, tickers: list[str]) -> pd.DataFrame:
        """Default batch implementation; providers with true batch
        endpoints (most paid APIs) should override this for speed."""
        rows = []
        for t in tickers:
            try:
                print(f"  fetching {t} ...")
                rows.append(self.get_stock(t))
            except Exception as e:
                print(f"  !! failed for {t}: {e}")
        return pd.DataFrame(rows)


class MFDataProvider(ABC):
    """Supplies mutual fund NAV histories."""

    @abstractmethod
    def get_nav_history(self, scheme_code: str) -> pd.DataFrame:
        """Full NAV history -> DataFrame [date, nav], oldest->newest,
        with .attrs scheme_name / category / fund_house."""

    def get_many(self, watchlist: dict) -> dict:
        out = {}
        for code, name in watchlist.items():
            try:
                print(f"  fetching {name} ({code}) ...")
                out[code] = self.get_nav_history(code)
            except Exception as e:
                print(f"  !! failed for {name}: {e}")
        return out


class BenchmarkProvider(ABC):
    """Supplies index histories for alpha / capture-ratio calculations."""

    @abstractmethod
    def get_history(self, ticker: str, period: str = "10y") -> pd.Series | None:
        """Daily index levels (date-indexed), or None on failure."""
