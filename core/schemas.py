"""
core/schemas.py — THE DATA CONTRACT.

This is the most important file for scalability. Every provider — free or
paid, today's or next year's — must return data in EXACTLY these shapes.
The analysis layer is written against these shapes and nothing else.

Result: swapping Yahoo for Zerodha Kite means writing ONE new provider file
and changing ONE line in config.py. Zero changes to analysis or main.
"""

# Canonical columns for a stock snapshot (one row per stock).
# A provider may return None for fields it can't supply — the scorer
# already handles gaps — but it must NOT invent new column names.
STOCK_SCHEMA = [
    "ticker", "name", "sector", "market_cap_cr", "price",
    # quality
    "roe", "roa", "profit_margin", "debt_to_equity",
    # growth
    "earnings_growth", "revenue_growth",
    # valuation
    "pe", "forward_pe", "pb", "dividend_yield",
    # momentum
    "six_month_return", "pct_from_52w_high", "above_200dma",
]

# Canonical mutual fund NAV history: DataFrame with these columns,
# sorted oldest -> newest, plus .attrs for metadata.
MF_NAV_SCHEMA = ["date", "nav"]
MF_ATTRS = ["scheme_name", "category", "fund_house"]


def conform_stock_row(row: dict) -> dict:
    """Force a provider's raw dict into the canonical stock schema."""
    return {col: row.get(col) for col in STOCK_SCHEMA}
