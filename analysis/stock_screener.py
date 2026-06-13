"""
analysis/stock_screener.py — PHASE 2: sector-aware scoring.

What changed vs Phase 1 (and why it matters):
  1. METRIC SELECTION IS SECTOR-SPECIFIC. A bank is no longer punished for
     "high debt" (deposits ARE its raw material) and is now judged on
     ROA and P/B like a real bank analyst would.
  2. RANKING IS WITHIN-SECTOR where your watchlist has >= MIN_SECTOR_SIZE
     stocks in that sector. Comparing TCS's P/E to a PSU bank's P/E was
     the single biggest flaw of Phase 1. When a sector group is too small,
     we fall back to whole-list ranking and FLAG it in the 'rank_scope'
     column so you know that score is weaker evidence.
"""

import pandas as pd
from config import STOCK_WEIGHTS, SECTOR_PROFILES, LOWER_IS_BETTER, MIN_SECTOR_SIZE

MOMENTUM_METRICS = ["six_month_return", "pct_from_52w_high"]  # + 200DMA flag
GROWTH_METRICS = ["earnings_growth", "revenue_growth"]


def _profile_for(sector: str) -> dict:
    return SECTOR_PROFILES.get(sector, SECTOR_PROFILES["default"])


def _pct_rank(series: pd.Series, metric: str) -> pd.Series:
    """Percentile rank 0-100 within whatever group `series` represents."""
    ascending = metric not in LOWER_IS_BETTER
    return series.rank(pct=True, ascending=ascending) * 100


def _pillar_score(group: pd.DataFrame, metrics: list[str]) -> pd.Series:
    parts = [_pct_rank(group[m], m) for m in metrics if m in group.columns]
    if not parts:
        return pd.Series(index=group.index, dtype=float)
    return pd.concat(parts, axis=1).mean(axis=1, skipna=True)


def _score_group(group: pd.DataFrame) -> pd.DataFrame:
    """Score one ranking group (a sector, or the whole list as fallback)."""
    g = group.copy()
    profile = _profile_for(g["sector"].iloc[0]) if g["sector"].nunique() == 1 \
        else SECTOR_PROFILES["default"]

    quality_metrics = list(profile["quality"])
    if "roce" in g.columns and g["roce"].notna().any():
        quality_metrics.append("roce")   # available with screener.in data
    g["quality_score"] = _pillar_score(g, quality_metrics)
    g["growth_score"] = _pillar_score(g, GROWTH_METRICS)
    g["valuation_score"] = _pillar_score(g, profile["valuation"])

    mom = pd.concat(
        [_pct_rank(g[m], m) for m in MOMENTUM_METRICS]
        + [g["above_200dma"].map({True: 100.0, False: 0.0})],
        axis=1,
    )
    g["momentum_score"] = mom.mean(axis=1, skipna=True)
    return g


def score_stocks(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sector"] = df["sector"].fillna("Unknown")

    sector_sizes = df["sector"].value_counts()
    big_sectors = sector_sizes[sector_sizes >= MIN_SECTOR_SIZE].index

    scored_parts = []

    # 1) sectors with enough peers: rank within the sector
    for sector in big_sectors:
        grp = _score_group(df[df["sector"] == sector])
        grp["rank_scope"] = f"sector ({sector}, n={len(grp)})"
        scored_parts.append(grp)

    # 2) everything else: rank together vs the whole watchlist, flagged
    rest = df[~df["sector"].isin(big_sectors)]
    if not rest.empty:
        if len(rest) == 1:
            # Ranking a stock against itself = meaningless perfect score.
            grp = rest.copy()
            for c in ["quality_score", "growth_score", "valuation_score", "momentum_score"]:
                grp[c] = float("nan")  # becomes neutral 50 in the composite
            grp["rank_scope"] = "no peers — neutral score, judge manually"
        else:
            grp = _score_group(rest)
            grp["rank_scope"] = "whole-list fallback (small sector group)"
        scored_parts.append(grp)

    s = pd.concat(scored_parts)

    s["total_score"] = (
        s["quality_score"].fillna(50) * STOCK_WEIGHTS["quality"]
        + s["growth_score"].fillna(50) * STOCK_WEIGHTS["growth"]
        + s["valuation_score"].fillna(50) * STOCK_WEIGHTS["valuation"]
        + s["momentum_score"].fillna(50) * STOCK_WEIGHTS["momentum"]
    ).round(1)

    return s.sort_values("total_score", ascending=False).reset_index(drop=True)


def print_stock_report(scored: pd.DataFrame):
    cols = [
        "ticker", "name", "sector", "pe", "roe",
        "quality_score", "growth_score", "valuation_score",
        "momentum_score", "total_score", "rank_scope",
    ]
    print("\n========== STOCK RANKINGS (sector-aware) ==========")
    print(scored[cols].round(1).to_string(index=False))

    # India-specific governance red flag (needs screener.in data)
    if "pledged_pct" in scored.columns:
        flagged = scored[scored["pledged_pct"].fillna(0) > 0]
        if not flagged.empty:
            print("\n!! GOVERNANCE WARNING - promoter shares pledged:")
            for _, r in flagged.iterrows():
                print(f"   {r['ticker']}: {r['pledged_pct']}% of promoter holding pledged")
            print("   Pledging above ~10-15% has preceded many Indian blowups. Investigate before buying.")
    print(
        "\nHow to read: scores are percentiles WITHIN the group named in rank_scope."
        "\nA total_score of 80 in a 3-stock sector is weaker evidence than 80 in a"
        "\n10-stock sector - group size matters. Cross-sector totals are NOT comparable;"
        "\nuse them to pick the best stock WITHIN each sector, then diversify across sectors."
    )
