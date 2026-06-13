"""
analysis/mf_analyzer.py — PHASE 2: benchmark- and category-relative fund analysis.

New vs Phase 1:
  * ALPHA (3y): fund's 3-year CAGR minus its benchmark index's 3-year CAGR.
    A midcap fund returning 18% sounds great — unless the midcap index did 22%.
    Alpha is the number professionals are actually paid for.
  * UPSIDE / DOWNSIDE CAPTURE: in months when the benchmark rose, what % of
    that rise did the fund capture? In falling months, what % of the fall did
    it absorb? The dream profile: upside > 100, downside < 100.
    Downside capture is arguably the best single risk metric in fund analysis.
  * CATEGORY-RELATIVE RANKING: funds are now percentile-ranked against funds
    in the SAME AMFI category (when you hold >= MIN_CATEGORY_SIZE of that
    category), so a small-cap fund is no longer "riskier" merely for being
    small-cap. Small groups fall back to all-fund ranking, flagged.

Rolling returns from Phase 1 are kept — they remain the most underrated metric.
"""

import numpy as np
import pandas as pd
from config import RISK_FREE_RATE, MF_WEIGHTS, MIN_CATEGORY_SIZE

TRADING_DAYS = 252


def analyze_fund(nav_df: pd.DataFrame, benchmark: pd.Series | None = None) -> dict:
    """
    nav_df: DataFrame [date, nav] oldest->newest.
    benchmark: optional daily index levels (pd.Series indexed by date).
    """
    nav = nav_df.set_index("date")["nav"]
    daily_ret = nav.pct_change().dropna()

    out = {
        "history_years": round((nav.index[-1] - nav.index[0]).days / 365.25, 1),
        "cagr_1y": _cagr(nav, 1),
        "cagr_3y": _cagr(nav, 3),
        "cagr_5y": _cagr(nav, 5),
        "volatility": round(daily_ret.std() * np.sqrt(TRADING_DAYS) * 100, 2),
        "max_drawdown": _max_drawdown(nav),
        "sharpe": _sharpe(daily_ret),
    }
    out.update(_rolling_3y(nav))
    out.update(_vs_benchmark(nav, benchmark))
    return out


# ---------- absolute metrics (Phase 1, unchanged) ----------

def _cagr(nav: pd.Series, years: int):
    cutoff = nav.index[-1] - pd.DateOffset(years=years)
    past = nav[nav.index <= cutoff]
    if past.empty:
        return None
    return round(((nav.iloc[-1] / past.iloc[-1]) ** (1 / years) - 1) * 100, 2)


def _max_drawdown(nav: pd.Series):
    clean = nav[nav > 0].dropna()
    if clean.empty:
        return None
    return round(((clean / clean.cummax() - 1) * 100).min(), 2)


def _sharpe(daily_ret: pd.Series):
    ann_vol = daily_ret.std() * np.sqrt(TRADING_DAYS)
    if ann_vol == 0:
        return None
    return round((daily_ret.mean() * TRADING_DAYS - RISK_FREE_RATE) / ann_vol, 2)


def _rolling_3y(nav: pd.Series) -> dict:
    monthly = nav.resample("ME").last().dropna()
    window = 36
    if len(monthly) <= window:
        return {"roll3y_avg": None, "roll3y_worst": None, "roll3y_pct_above_12": None}
    roll = ((monthly / monthly.shift(window)) ** (1 / 3) - 1).dropna() * 100
    return {
        "roll3y_avg": round(roll.mean(), 2),
        "roll3y_worst": round(roll.min(), 2),
        "roll3y_pct_above_12": round((roll > 12).mean() * 100, 1),
    }


# ---------- benchmark-relative metrics (Phase 2, new) ----------

def _vs_benchmark(nav: pd.Series, benchmark: pd.Series | None) -> dict:
    empty = {"benchmark_cagr_3y": None, "alpha_3y": None,
             "upside_capture": None, "downside_capture": None}
    if benchmark is None or benchmark.empty:
        return empty

    bench_cagr = _cagr(benchmark, 3)
    fund_cagr = _cagr(nav, 3)
    alpha = round(fund_cagr - bench_cagr, 2) if (
        fund_cagr is not None and bench_cagr is not None) else None

    # monthly returns over the common history for capture ratios
    f_m = nav.resample("ME").last().pct_change().dropna()
    b_m = benchmark.resample("ME").last().pct_change().dropna()
    joined = pd.concat([f_m, b_m], axis=1, keys=["fund", "bench"]).dropna()
    if len(joined) < 24:  # need at least 2 years of overlap to be meaningful
        return {**empty, "benchmark_cagr_3y": bench_cagr, "alpha_3y": alpha}

    up = joined[joined["bench"] > 0]
    down = joined[joined["bench"] < 0]
    upside = round(up["fund"].mean() / up["bench"].mean() * 100, 1) if len(up) else None
    downside = round(down["fund"].mean() / down["bench"].mean() * 100, 1) if len(down) else None

    return {
        "benchmark_cagr_3y": bench_cagr,
        "alpha_3y": alpha,
        "upside_capture": upside,
        "downside_capture": downside,
    }


# ---------- category-relative scoring ----------

def _score_group(df: pd.DataFrame) -> pd.DataFrame:
    g = df.copy()

    def pr(col, higher_better=True):
        return g[col].rank(pct=True, ascending=higher_better) * 100

    g["returns_score"] = pd.concat(
        [pr("cagr_1y"), pr("cagr_3y"), pr("cagr_5y"), pr("alpha_3y")], axis=1
    ).mean(axis=1, skipna=True)

    g["consistency_score"] = pd.concat(
        [pr("roll3y_avg"), pr("roll3y_worst"), pr("roll3y_pct_above_12")], axis=1
    ).mean(axis=1, skipna=True)

    # downside_capture: LOWER is better. max_drawdown is negative: higher (nearer 0) better.
    g["risk_score"] = pd.concat(
        [pr("volatility", False), pr("max_drawdown"), pr("sharpe"),
         pr("downside_capture", False)], axis=1
    ).mean(axis=1, skipna=True)

    return g


def score_funds(metrics_list: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(metrics_list)
    df["category"] = df.get("category", pd.Series(dtype=str)).fillna("Unknown")

    cat_sizes = df["category"].value_counts()
    big_cats = cat_sizes[cat_sizes >= MIN_CATEGORY_SIZE].index

    parts = []
    for cat in big_cats:
        grp = _score_group(df[df["category"] == cat])
        grp["rank_scope"] = f"category ({cat}, n={len(grp)})"
        parts.append(grp)

    rest = df[~df["category"].isin(big_cats)]
    if not rest.empty:
        if len(rest) == 1:
            grp = rest.copy()
            for c in ["returns_score", "consistency_score", "risk_score"]:
                grp[c] = float("nan")  # neutral 50 in composite
            grp["rank_scope"] = "no peers — neutral score, judge manually"
        else:
            grp = _score_group(rest)
            grp["rank_scope"] = "all-funds fallback (small category group)"
        parts.append(grp)

    s = pd.concat(parts)
    s["total_score"] = (
        s["returns_score"].fillna(50) * MF_WEIGHTS["returns"]
        + s["consistency_score"].fillna(50) * MF_WEIGHTS["consistency"]
        + s["risk_score"].fillna(50) * MF_WEIGHTS["risk"]
    ).round(1)

    return s.sort_values("total_score", ascending=False).reset_index(drop=True)


def print_mf_report(scored: pd.DataFrame):
    cols = [
        "scheme_name", "cagr_3y", "alpha_3y", "upside_capture",
        "downside_capture", "roll3y_worst", "max_drawdown", "total_score",
        "rank_scope",
    ]
    cols = [c for c in cols if c in scored.columns]
    print("\n========== MUTUAL FUND RANKINGS (benchmark & category relative) ==========")
    print(scored[cols].to_string(index=False))
    print(
        "\nalpha_3y: fund 3y CAGR minus its benchmark's. Positive = the manager added value."
        "\ndownside_capture: % of benchmark falls the fund absorbed. Below 100 = defensive."
        "\nrank_scope shows WHO each fund was ranked against - category peers when possible."
    )
