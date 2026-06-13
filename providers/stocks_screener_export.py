"""
providers/stocks_screener_export.py — HYBRID provider:
  * FUNDAMENTALS from a screener.in Excel/CSV export (best free Indian data:
    ROCE, multi-year growth, promoter holding & pledging — Yahoo has none of these)
  * MOMENTUM (price trend metrics) still auto-fetched from Yahoo

How to use:
  1. Make a free account at https://www.screener.in
  2. Build a watchlist or screen with your stocks. Add columns you care about —
     recommended: ROCE, ROE, Debt to equity, OPM, Sales growth 3Years,
     Profit growth 3Years, Promoter holding, Pledged percentage, P/E, CMP
     (free accounts may limit rows per export — verify on the site)
  3. Click "Export to Excel", save the file into this project folder as:
         screener_export.xlsx     (name configurable in config.py)
  4. In config.py set:  STOCK_PROVIDER = "screener_export"
  5. Run python main.py as usual. Refresh the export weekly/monthly.

The column names in screener.in exports vary with your chosen columns, so this
provider matches them flexibly via the ALIASES table below. Unrecognized
columns are simply ignored; missing ones become None (scorer handles gaps).
"""

import re
from pathlib import Path

import pandas as pd

from providers.base import StockDataProvider
from core.schemas import conform_stock_row

# canonical_field -> list of screener.in column-name fragments that mean it
ALIASES = {
    "name": ["name"],
    "nse_code": ["nse code"],
    "bse_code": ["bse code"],
    "sector": ["industry", "sector"],
    "price": ["current price", "cmp"],
    "market_cap_cr": ["market capitalization", "market cap"],
    "pe": ["price to earning", "p/e"],
    "pb": ["price to book", "cmp / bv", "p/b"],
    "roe": ["return on equity", "roe"],
    "roce": ["return on capital employed", "roce"],
    "debt_to_equity": ["debt to equity"],
    "profit_margin": ["opm", "net profit margin", "npm"],
    "dividend_yield": ["dividend yield"],
    "earnings_growth": ["profit growth 3years", "profit growth 3 years", "profit growth"],
    "revenue_growth": ["sales growth 3years", "sales growth 3 years", "sales growth"],
    "promoter_holding": ["promoter holding"],
    "pledged_pct": ["pledged percentage", "pledged"],
}


def _norm(col: str) -> str:
    return re.sub(r"\s+", " ", str(col)).strip().lower()


class ScreenerExportProvider(StockDataProvider):

    def __init__(self, export_path: str = "screener_export.xlsx",
                 momentum_from_yahoo: bool = True):
        path = Path(export_path)
        if not path.exists():
            raise FileNotFoundError(
                f"screener.in export not found at '{export_path}'.\n"
                "Export your watchlist from https://www.screener.in (see the "
                "header of providers/stocks_screener_export.py for steps) and "
                "save it in the project folder, or fix SCREENER_EXPORT_PATH in config.py."
            )
        raw = (pd.read_excel(path) if path.suffix in {".xlsx", ".xls"}
               else pd.read_csv(path))

        # map screener columns -> canonical fields
        colmap = {}
        for canonical, fragments in ALIASES.items():
            for col in raw.columns:
                if any(frag in _norm(col) for frag in fragments):
                    colmap[canonical] = col
                    break
        if "nse_code" not in colmap and "name" not in colmap:
            raise ValueError(
                "Could not find an 'NSE Code' or 'Name' column in the export — "
                f"columns present: {list(raw.columns)}"
            )

        # index rows by NSE ticker (with .NS suffix to match the watchlist)
        self.rows: dict[str, dict] = {}
        for _, r in raw.iterrows():
            rec = {k: _num(r[c]) if k not in {"name", "sector", "nse_code", "bse_code"}
                   else r[c] for k, c in colmap.items()}
            code = str(rec.get("nse_code") or "").strip()
            if code and code.lower() != "nan":
                self.rows[f"{code.upper()}.NS"] = rec

        self.momentum_from_yahoo = momentum_from_yahoo
        self._yahoo = None
        print(f"  screener.in export loaded: {len(self.rows)} companies, "
              f"{len(colmap)} fields mapped ({', '.join(colmap)})")

    def get_stock(self, ticker: str) -> dict:
        rec = self.rows.get(ticker)
        if rec is None:
            raise KeyError(
                f"{ticker} not in the screener.in export — add it to your "
                "screener.in watchlist and re-export.")

        row = conform_stock_row({
            "ticker": ticker,
            "name": rec.get("name"),
            "sector": rec.get("sector"),
            "market_cap_cr": rec.get("market_cap_cr"),
            "price": rec.get("price"),
            "roe": rec.get("roe"),
            "roa": None,
            "profit_margin": rec.get("profit_margin"),
            "debt_to_equity": rec.get("debt_to_equity"),
            "earnings_growth": rec.get("earnings_growth"),
            "revenue_growth": rec.get("revenue_growth"),
            "pe": rec.get("pe"),
            "pb": rec.get("pb"),
            "dividend_yield": rec.get("dividend_yield"),
        })
        # extended India-specific fields (extra columns; scorer ignores unknowns,
        # the report prints them as governance signals)
        row["roce"] = rec.get("roce")
        row["promoter_holding"] = rec.get("promoter_holding")
        row["pledged_pct"] = rec.get("pledged_pct")

        if self.momentum_from_yahoo:
            row.update(self._momentum(ticker))
        return row

    def _momentum(self, ticker: str) -> dict:
        """Pull only price-trend fields from Yahoo; degrade gracefully offline."""
        try:
            if self._yahoo is None:
                from providers.stocks_yahoo import YahooStockProvider
                self._yahoo = YahooStockProvider()
            y = self._yahoo.get_stock(ticker)
            return {k: y.get(k) for k in
                    ("six_month_return", "pct_from_52w_high", "above_200dma")}
        except Exception as e:
            print(f"  (momentum unavailable for {ticker}: {e})")
            return {}


def _num(x):
    """screener exports sometimes have '1,234.5' strings or blanks."""
    if pd.isna(x):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None
