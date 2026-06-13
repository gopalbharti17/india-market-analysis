# India Market Analysis Agent — Starter Kit (Phase 1)

A free, transparent system to screen Indian stocks and mutual funds, with an optional AI agent layer on top. You control the watchlists and scoring weights; the code shows its work.

## What's in the box

```
india-market-agent/
├── config.py                  <- YOUR control panel (watchlists, weights, PROVIDER CHOICE)
├── main.py                    <- run this: fetches, scores, ranks everything
├── agent.py                   <- optional AI chat layer (needs Claude API key)
├── core/
│   ├── schemas.py             <- canonical data contract all providers must honor
│   └── cache.py               <- SQLite cache (don't fetch the same data twice)
├── providers/
│   ├── base.py                <- abstract interfaces
│   ├── registry.py            <- provider name -> class factory
│   ├── stocks_yahoo.py        <- FREE stock data (active)
│   ├── stocks_kite.py         <- PAID Zerodha Kite stub (fill in when you subscribe)
│   ├── mf_mfapi.py            <- FREE AMFI fund NAVs (active)
│   └── benchmarks_yahoo.py    <- FREE index data (active)
└── analysis/
    ├── stock_screener.py      <- sector-aware scoring
    └── mf_analyzer.py         <- benchmark & category-relative fund analysis
```

## Upgrading to paid data later (the whole point of this structure)

1. Subscribe to the API (e.g. Zerodha Kite Connect).
2. Open `providers/stocks_kite.py`, follow its header instructions, fill the TODOs
   so it returns the canonical schema from `core/schemas.py`.
3. In `config.py`, change `STOCK_PROVIDER = "yahoo"` to `"kite"`.
That's it — screener, agent and reports are untouched. The same pattern adds
TrueData, Global Data Feeds, screener.in exports, or any future source: one new
file in `providers/`, one entry in `registry.py`, one name in `config.py`.
Providers can also be MIXED (e.g. Kite for prices, Yahoo for fundamentals).

## Old tree (Phase 1, for reference)

```
india-market-agent/
├── config.py                  <- YOUR control panel (watchlists, weights)
├── main.py                    <- run this: fetches, scores, ranks everything
├── agent.py                   <- optional AI chat layer (needs Claude API key)
├── requirements.txt
├── data_fetchers/
│   ├── stocks.py              <- Yahoo Finance (NSE stocks, free)
│   └── mutual_funds.py        <- AMFI NAV data via mfapi.in (free)
└── analysis/
    ├── stock_screener.py      <- quality/growth/valuation/momentum scoring
    └── mf_analyzer.py         <- CAGR, rolling returns, drawdown, Sharpe
```

## Project roadmap
**ROADMAP.md** is the pick-up-anytime guide: current status, next steps with
acceptance criteria, and copy-paste prompts to resume work with Claude or
Claude Code. Start there when returning to the project.

## Methodology
The complete scoring logic — every formula, design decision, known weakness,
and the improvement backlog — is documented in **METHODOLOGY.md**. Read it
before tuning weights; update it whenever scoring logic changes.

## Setup (one time, ~5 minutes)

1. **Install Python 3.10+** from https://python.org if you don't have it
   (during install on Windows, tick "Add Python to PATH").

2. **Open a terminal** in this folder and create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # Mac/Linux
   ```

3. **Install the libraries:**
   ```
   pip install -r requirements.txt
   ```

## Run it

```
python main.py
```

You'll see ranked tables for both stocks and mutual funds, plus two CSV files
(`stock_rankings.csv`, `mf_rankings.csv`) you can open in Excel.

## Make it yours

Everything you'd want to change lives in `config.py`:

- **Add stocks**: append NSE tickers with `.NS` (e.g. `"WIPRO.NS"`).
- **Add funds**: find any fund's scheme code at https://www.mfapi.in
  (search the fund name, copy the number).
- **Change your investing style**: edit `STOCK_WEIGHTS` / `MF_WEIGHTS`.
  Value investor? Raise `valuation`. Long-term quality buyer? Raise `quality`.

## How to read the scores

- Scores are **percentile rankings within your own watchlist** (0–100).
  A 90 means "better than 90% of the list on that pillar" — it is NOT an
  absolute buy signal.
- For mutual funds, pay special attention to `roll3y_worst`: the worst
  3-year return any investor in that fund ever experienced. It separates
  consistent funds from lucky ones.
- Compare like with like: a small-cap fund will look "riskier" than a
  large-cap fund because it IS riskier — that's the data being honest.

## Better fundamentals: the screener.in bridge (recommended)

Yahoo's Indian fundamentals are the weakest data in the free pipeline. The fix:
1. Free account at https://www.screener.in -> build a watchlist with your stocks
2. Add columns: ROCE, ROE, Debt to equity, OPM, Sales growth 3Years,
   Profit growth 3Years, Promoter holding, Pledged percentage, P/E
3. Export to Excel -> save as `screener_export.xlsx` in this folder
4. In config.py: STOCK_PROVIDER = "screener_export"

You get analyst-grade Indian fundamentals (3-year growth trends, ROCE) plus an
automatic GOVERNANCE WARNING whenever any promoter shares are pledged.
Momentum data still flows automatically from Yahoo. Refresh the export weekly.

## Memory: the engine's research record

Every run is appended to `research_history.db` (BACK THIS FILE UP — it is your
accumulated research record; the cache db is disposable, this one is not).
Each report now ends with a CHANGES section: score/rank movers with the pillar
that drove them, new entries, removals, and newly-pledged promoter shares.
Query any entity's trend across runs:
    python history_report.py stock TCS.NS
    python history_report.py fund 122639
The more regularly you run the pipeline (weekly is ideal), the richer this gets.

## Phase 3 (optional): the AI agent

`agent.py` adds a chat interface where Claude calls your analysis functions
and explains results in plain English. It needs an Anthropic API key
(usage-based pricing — see the comments at the top of `agent.py` for setup).
The core screener never needs it.

## Roadmap (what we build next)

- **Phase 2**: deeper fundamentals (promoter pledging, sector-relative P/E),
  expense ratios for funds, benchmark comparison vs Nifty indices
- **Phase 3**: the agent layer + RAG over annual reports
- **Phase 4**: Streamlit dashboard, alerts, and tracking how past picks performed

## Known limits of free data (be aware)

- Yahoo Finance fundamentals for Indian stocks occasionally have gaps or lag
  a quarter. The scorer handles missing fields gracefully, but cross-check
  anything surprising on screener.in before acting.
- mfapi.in mirrors official AMFI NAVs and is reliable, but is a community
  service — if it's ever down, retry later.

## Disclaimer

This is a research and learning tool for your personal use. It does not give
investment advice, and ranking high in your watchlist doesn't mean a security
will perform well. Under SEBI regulations, sharing buy/sell recommendations
with others requires registration as an Investment Adviser.
