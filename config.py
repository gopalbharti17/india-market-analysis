"""
config.py — Your control panel.
Edit this file to change which stocks/funds are analyzed and how they're scored.
You should never need to touch the other files for day-to-day use.
"""

# ---------------------------------------------------------------
# STOCK WATCHLIST
# NSE tickers need the ".NS" suffix for Yahoo Finance.
# (BSE tickers use ".BO", e.g. "500325.BO" for Reliance on BSE)
# Start small; add more once everything works.
# ---------------------------------------------------------------
STOCK_WATCHLIST = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "ITC.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    # Added to enable sector-aware ranking (need 3+ per sector)
    "WIPRO.NS",        # Technology -> now 4 (TCS, INFY, WIPRO, HCLTECH)
    "HCLTECH.NS",      # Technology
    "AXISBANK.NS",     # Financial Services -> now 4 (HDFC, ICICI, AXIS, KOTAK)
    "KOTAKBANK.NS",    # Financial Services
    "HINDUNILVR.NS",   # Consumer Defensive -> now 3 (ITC, HUL, NESTLE)
    "NESTLEIND.NS",    # Consumer Defensive
]

# ---------------------------------------------------------------
# MUTUAL FUND WATCHLIST
# These are AMFI scheme codes. Find any fund's code at:
#   https://www.mfapi.in  (search by fund name)
# The ones below are examples (direct-growth plans).
# ---------------------------------------------------------------
MF_WATCHLIST = {
    "120503": "Axis Bluechip Fund - Direct Growth",
    "122639": "Parag Parikh Flexi Cap Fund - Direct Growth",
    "118989": "HDFC Mid-Cap Opportunities - Direct Growth",
    "119598": "SBI Small Cap Fund - Direct Growth",
    "120716": "UTI Nifty 50 Index Fund - Direct Growth",
    "125497": "Mirae Asset Large Cap - Direct Growth",
}

# ---------------------------------------------------------------
# STOCK SCORING WEIGHTS (must add up to 1.0)
# Tilt these toward your style:
#   value investor  -> raise "valuation"
#   growth investor -> raise "growth"
#   momentum trader -> raise "momentum"
# ---------------------------------------------------------------
STOCK_WEIGHTS = {
    "quality": 0.30,     # ROE, profit margins, low debt
    "growth": 0.25,      # earnings & revenue growth
    "valuation": 0.25,   # P/E vs peers (lower = better)
    "momentum": 0.20,    # 6-month price trend, vs 200-day average
}

# ---------------------------------------------------------------
# MUTUAL FUND SCORING WEIGHTS (must add up to 1.0)
# ---------------------------------------------------------------
MF_WEIGHTS = {
    "returns": 0.40,       # 1y / 3y / 5y CAGR
    "consistency": 0.30,   # rolling 3-year returns (does it deliver in ALL periods?)
    "risk": 0.30,          # volatility + max drawdown (lower = better)
}

# Risk-free rate used in Sharpe ratio (approx. Indian 10y G-Sec yield)
RISK_FREE_RATE = 0.07

# ---------------------------------------------------------------
# PHASE 2: SECTOR-AWARE STOCK SCORING
# Different sectors need different metrics. Banks/NBFCs: debt ratios are
# meaningless and P/B matters most. The "default" profile applies to any
# sector not listed here. Metric lists per pillar; "lower_better" marks
# metrics where smaller values score higher.
# ---------------------------------------------------------------
SECTOR_PROFILES = {
    "default": {
        "quality": ["roe", "profit_margin", "debt_to_equity"],
        "valuation": ["pe", "pb"],
    },
    "Financial Services": {
        "quality": ["roe", "roa"],          # no debt_to_equity for lenders
        "valuation": ["pb", "pe"],          # P/B is king for financials
    },
}
LOWER_IS_BETTER = {"debt_to_equity", "pe", "pb"}

# Rank within a sector only if it has at least this many stocks in your
# watchlist; otherwise fall back to ranking vs the whole list (flagged).
MIN_SECTOR_SIZE = 3

# ---------------------------------------------------------------
# PHASE 2: MUTUAL FUND BENCHMARKS
# Maps words found in a fund's AMFI category to a Yahoo Finance index ticker.
# First match wins (checked top to bottom). Anything unmatched -> Nifty 50.
# You can change/extend these freely.
# ---------------------------------------------------------------
CATEGORY_BENCHMARKS = [
    ("small cap", "^CNXSC"),       # Nifty Smallcap 100
    ("mid cap", "^NSEMDCP50"),     # Nifty Midcap 50
    ("midcap", "^NSEMDCP50"),
    ("bank", "^NSEBANK"),          # Nifty Bank
    ("it ", "^CNXIT"),             # Nifty IT
]
DEFAULT_BENCHMARK = "^NSEI"        # Nifty 50

# Rank funds within their own category only if the category has at least
# this many funds in your watchlist; otherwise rank vs all funds (flagged).
MIN_CATEGORY_SIZE = 3

# ---------------------------------------------------------------
# PHASE 2.5: DATA PROVIDERS — the scalability switchboard.
# When you subscribe to a paid API later, change the name here.
# Nothing else in the system needs to change.
#   Stock options today: "yahoo" (free) | "kite" (stub, fill when subscribed)
# ---------------------------------------------------------------
STOCK_PROVIDER = "yahoo"
MF_PROVIDER = "mfapi"
BENCHMARK_PROVIDER = "nse_tri"  # official TRI; auto-falls back to "yahoo" price index if NSE endpoint is down

# Cache freshness (hours). Lower = fresher data, more API calls.
CACHE_MAX_AGE_HOURS = 12

# Path to your screener.in export file (used when STOCK_PROVIDER = "screener_export")
SCREENER_EXPORT_PATH = "screener_export.xlsx"
