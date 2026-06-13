# SCORING METHODOLOGY
### India Market Analysis Agent — v6 · June 2026
**Status: HYPOTHESIS — not yet validated by backtesting. See §8.**

This document is the single source of truth for how every score in the system
is produced: the formulas, the design decisions and their reasons, the known
weaknesses, and the improvement backlog. Code implements this document; when
they disagree, one of them has a bug.

---

## 1. Design philosophy

1. **Relative, not absolute.** Every score is a percentile rank against a peer
   group, never a verdict. A score of 80 means "better than 80% of its
   comparison group on the weighted pillars" — nothing more.
2. **Transparent over clever.** Every score must be traceable by hand to its
   inputs. No black boxes; complexity is added only when evidence demands it.
3. **Honest about evidence strength.** Small peer groups produce weak
   evidence; the system flags this (`rank_scope`) instead of hiding it.
4. **Graceful degradation.** Missing data never crashes a run; a missing
   metric simply doesn't contribute to its pillar (mean of available metrics,
   `skipna=True`), and a fully missing pillar defaults to neutral 50.

---

## 2. The scoring pipeline (both asset classes)

```
raw metrics -> peer group assignment -> percentile rank per metric (0-100)
            -> pillar score = mean of its metrics' percentiles
            -> total score = weighted sum of pillar scores (weights: config.py)
            -> sort, flag evidence strength, narrate changes vs last run
```

**Percentile ranking:** `pandas .rank(pct=True) * 100` within the peer group.
Metrics where lower is better (P/E, P/B, debt/equity, volatility, downside
capture) are ranked ascending-inverted (config: `LOWER_IS_BETTER`).

**Singleton guard:** a peer group of one cannot be ranked against itself
(it would always score 100). Such entities receive neutral NaN→50 pillar
scores and `rank_scope = "no peers — judge manually"`.

---

## 3. Stock scoring

### 3.1 Peer groups
- Within sector, if the watchlist holds ≥ `MIN_SECTOR_SIZE` (default 3)
  stocks of that sector (sector label: data provider's classification).
- Otherwise: pooled "whole-list fallback", flagged in `rank_scope`.
- **Rationale:** cross-sector ratio comparison (bank P/E vs IT P/E) is the
  classic retail screening error; sector-relative is the analyst standard.
- **Known weakness:** sector labels come from the data provider and may
  misclassify; tiny sectors fall back to a noisy pooled comparison. (§7-W3)

### 3.2 Pillars, metrics, formulas

| Pillar (weight) | Metrics | Direction |
|---|---|---|
| Quality (0.30) | ROE %, profit margin (OPM/NPM) %, debt/equity; ROCE % added when present (screener.in data); banks use ROE + ROA, no D/E | higher better except D/E |
| Growth (0.25) | earnings growth %, revenue growth % (3-yr versions when screener.in data present, else provider's trailing) | higher better |
| Valuation (0.25) | P/E, P/B (banks: P/B emphasized by profile) | lower better |
| Momentum (0.20) | 6-month price return %; % below 52-week high; above/below 200-day moving average (binary 100/0) | higher / closer / above better |

Momentum formulas (from ~1y daily closes):
- `six_month_return = (close_t / close_{t-126} − 1) × 100`
- `pct_from_52w_high = (close_t / max(close, 1y) − 1) × 100`  (≤ 0)
- `above_200dma = close_t > mean(close, last 200 sessions)`

### 3.3 Sector profiles (`config.SECTOR_PROFILES`)
- `default`: quality = [roe, profit_margin, debt_to_equity]; valuation = [pe, pb]
- `Financial Services`: quality = [roe, roa]; valuation = [pb, pe]
- **Rationale:** leverage is a bank's raw material, not a weakness; book
  value drives lender valuation. Extend this table per sector as study deepens.

### 3.4 Governance overlay (not scored — reported)
`pledged_pct` (promoter shares pledged, screener.in data) triggers a printed
warning at any value > 0, and the memory layer flags every increase.
**Design decision:** deliberately NOT folded into the numeric score — pledging
is a discrete risk event demanding human investigation, and averaging it into
a composite would dilute exactly the signal that must not be diluted.

### 3.5 Pillar weights (0.30 / 0.25 / 0.25 / 0.20)
Set by judgment: quality slightly leading reflects the long-horizon research
purpose; momentum trailing reflects its shorter half-life. **These weights
are the least defensible numbers in the system** until backtested (§8).

---

## 4. Mutual fund scoring

### 4.1 Peer groups
Within AMFI category when the watchlist holds ≥ `MIN_CATEGORY_SIZE` (3) funds
of it; else all-funds fallback, flagged. Singleton guard applies.

### 4.2 Pillars, metrics, formulas

**Returns (0.40):** CAGR 1y/3y/5y + alpha_3y.
- `CAGR_n = ((NAV_t / NAV_{t−n yrs})^{1/n} − 1) × 100`
- `alpha_3y = fund CAGR_3y − benchmark CAGR_3y`

**Consistency (0.30):** rolling 3-year window stats, monthly steps, full history:
- `roll = (NAV_m / NAV_{m−36})^{1/3} − 1` for every month m
- `roll3y_avg` = mean; `roll3y_worst` = min (worst outcome any 3-yr investor
  ever experienced); `roll3y_pct_above_12` = share of windows beating 12% p.a.
- **Rationale:** point-to-point CAGR depends on the start date; rolling
  returns measure the experience of *all* possible investors. The single most
  diagnostic fund metric in this system.

**Risk (0.30):** annualized volatility = `std(daily ret) × √252 × 100`;
max drawdown = `min(NAV/cummax(NAV) − 1) × 100`;
Sharpe = `(mean daily ret × 252 − rf) / (std daily ret × √252)`, rf = 0.07;
downside capture (lower better) — see 4.3.

### 4.3 Benchmark-relative metrics
Monthly returns of fund and benchmark over common history (≥ 24 months
required, else None):
- `upside_capture = mean(fund ret | bench up) / mean(bench ret | bench up) × 100`
- `downside_capture` = same over bench-down months. Dream profile: up > 100, down < 100.

Benchmark assignment: AMFI category keyword → index (config:
`CATEGORY_BENCHMARKS`); unmatched → Nifty 50.

**TRI correction (v5):** benchmarks default to NSE official Total Return
Indices. Fund NAVs include dividends; price indices don't; SEBI mandates TRI
benchmarking. On TRI fetch failure the system falls back to price indices
WITH A PRINTED WARNING (alpha then overstated ~1–1.5%/yr).

### 4.4 Weights (0.40 / 0.30 / 0.30)
Judgment-set; same caveat as §3.5.

---

## 5. Data lineage

| Data | Source | Trust notes |
|---|---|---|
| Fund NAVs | AMFI via mfapi.in | Official origin; best available |
| Benchmarks | NSE TRI (niftyindices.com), fallback Yahoo price | TRI = correct yardstick; fallback flagged |
| Stock prices/momentum | Yahoo Finance | Adequate EOD; occasional gaps |
| Stock fundamentals | Yahoo (default) or screener.in export (recommended) | Yahoo: lagging, snapshot-only. screener.in: 3-yr trends, ROCE, pledging |
| Cache | SQLite, 12–24h TTL | Disposable |
| History | research_history.db, append-only | PRECIOUS — back up |

---

## 6. Memory & change attribution (v6)
Every run snapshots all metrics+scores. The change report computes, per
entity: Δtotal_score, Δrank, and attributes the move to the pillar with the
largest absolute change ("driven by growth −40"). Pledging increases always
reported. Significance thresholds: |Δscore| ≥ 5 or |Δrank| ≥ 2 (function args).

---

## 7. Known weaknesses (ranked by severity)

- **W1 — Unvalidated weights.** All pillar weights are judgment. The composite
  is a hypothesis until §8 happens. *Severity: high.*
- **W2 — Watchlist selection bias.** The engine ranks only what the user
  chose; user bias runs upstream of all analysis. Mitigation: universe-wide
  screen exports. *High.*
- **W3 — Peer-group fragility.** Small sectors/categories → weak evidence
  (flagged but still weak); provider sector labels imperfect. *Medium.*
- **W4 — Snapshot fundamentals on the Yahoo path.** No trend awareness unless
  screener.in data is used. *Medium (mitigated by screener provider).*
- **W5 — Equal metric weights within pillars.** ROE counts the same as
  margin; no evidence behind that either. *Medium.*
- **W6 — No qualitative inputs.** Management, moats, accounting quality,
  forensic signals beyond pledging: invisible. *Medium-high, by design until
  the document-reading agent phase.*
- **W7 — Momentum simplicity.** Three crude signals; no volatility
  adjustment, no relative-strength vs index. *Low-medium.*
- **W8 — Capture-ratio sensitivity.** Short overlap windows make capture
  ratios noisy; 24-month floor is a partial guard. *Low.*

---

## 8. Validation plan (the missing pillar)
The backtest that converts hypothesis → evidence (or honestly refutes it):
1. Reconstruct historical scores at quarterly intervals over ≥ 10 years
   (needs point-in-time fundamentals — beware look-ahead bias, the classic
   backtest killer: never let a score "know" data published after its date).
2. Measure forward 1y returns of top-quintile vs bottom-quintile scores.
3. Test each pillar separately, then the composite; tune weights only on a
   training window, verify on held-out years.
4. Publish the result IN THIS DOCUMENT either way. A negative result is also
   success: it redirects effort to indexing before money learns it the hard way.

---

## 9. Improvement backlog (beyond §8)
universe-wide discovery scoring · self-relative valuation bands (P/E vs own
10-yr range) · MF portfolio-overlap analysis · expense-ratio & exit-load
ingestion · trend-slope factors (ROCE direction, margin trajectory) ·
document-reading agent (annual reports, concalls) · per-security research-note
generation · scheduled runs + alerting.

## 10. Methodology changelog
- v1: 4-pillar stocks + MF absolute metrics; whole-list percentiles
- v2: sector-aware profiles & in-sector ranking; alpha + capture ratios;
  category-relative funds; singleton guard
- v3: provider architecture + cache (no scoring change)
- v4: screener.in fundamentals; ROCE into quality; pledging overlay
- v5: TRI benchmarks with flagged fallback (alpha correction)
- v6: memory, change attribution, trend queries

**Rule for the future: any scoring change must update this file in the same
commit, with rationale, and append to this changelog.**
