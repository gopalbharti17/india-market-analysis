"""
main.py — Run the whole pipeline:  python main.py
Providers are chosen in config.py; this file never knows which API is behind them.
"""

from config import (
    STOCK_WATCHLIST, MF_WATCHLIST,
    STOCK_PROVIDER, MF_PROVIDER, BENCHMARK_PROVIDER,
)
from providers.registry import (
    get_stock_provider, get_mf_provider, get_benchmark_provider,
)
from providers.benchmarks_yahoo import benchmark_for_category
from analysis.stock_screener import score_stocks, print_stock_report
from core.history import record_run, print_changes, previous_run
from analysis.mf_analyzer import analyze_fund, score_funds, print_mf_report
import report as _report
import json
import pandas as pd


def _collect_changes(kind, current, id_col, run_ts):
    """Return changes as a list of dicts for the HTML report."""
    from core.history import PILLARS
    prev = previous_run(kind, run_ts)
    if prev is None:
        return []
    prev_map = {r.entity_id: r for r in prev.itertuples()}
    prev_payload = {r.entity_id: json.loads(r.payload) for r in prev.itertuples()}
    out = []
    for rank, (_, cur) in enumerate(current.iterrows(), start=1):
        eid = str(cur[id_col])
        p = prev_map.get(eid)
        if p is None:
            out.append({"kind": "NEW", "text": f"{eid} enters the list at rank {rank}"})
            continue
        score_move = (cur["total_score"] or 0) - (p.total_score or 0)
        rank_move = p.rank - rank
        if abs(score_move) >= 5 or abs(rank_move) >= 2:
            driver, driver_move = "", 0.0
            for pillar in PILLARS[kind]:
                old = prev_payload[eid].get(pillar)
                new = cur.get(pillar)
                if old is not None and pd.notna(new):
                    move = float(new) - float(old)
                    if abs(move) > abs(driver_move):
                        driver, driver_move = pillar, move
            arrow = "UP" if score_move > 0 else "DOWN"
            why = (f" — driven by {driver.replace('_score', '')} "
                   f"{'+' if driver_move > 0 else ''}{driver_move:.0f}") if driver else ""
            name = cur.get("name") or cur.get("scheme_name") or eid
            out.append({"kind": arrow,
                        "text": f"{name}: score {p.total_score:.0f} → {cur['total_score']:.0f}, "
                                f"rank {p.rank} → {rank}{why}"})
        pledged = cur.get("pledged_pct")
        old_pl = prev_payload[eid].get("pledged_pct") or 0
        if pd.notna(pledged) and float(pledged or 0) > float(old_pl):
            out.append({"kind": "FLAG",
                        "text": f"{eid} promoter pledging rose {old_pl} → {pledged}%"})
    gone = set(prev_map) - set(str(x) for x in current[id_col])
    for eid in gone:
        out.append({"kind": "REMOVED", "text": f"{eid} removed (was rank {prev_map[eid].rank})"})
    return out


_stock_scored = None
_mf_scored = None
_stock_changes = []
_mf_changes = []
_last_run_ts = None


def run_stocks():
    global _stock_scored, _stock_changes, _last_run_ts
    print(f"\n[1/2] Fetching stock data (provider: {STOCK_PROVIDER}) ...")
    provider = get_stock_provider(STOCK_PROVIDER)
    raw = provider.get_many(STOCK_WATCHLIST)
    if raw.empty:
        print("No stock data fetched — check your internet connection / tickers.")
        return
    scored = score_stocks(raw)
    print_stock_report(scored)
    run_ts = record_run("stock", scored, id_col="ticker")
    _last_run_ts = run_ts
    _stock_changes = _collect_changes("stock", scored, "ticker", run_ts)
    print_changes("stock", scored, id_col="ticker", run_ts=run_ts)
    scored.to_csv("stock_rankings.csv", index=False)
    print("Saved -> stock_rankings.csv")
    _stock_scored = scored


def run_mutual_funds():
    global _mf_scored, _mf_changes
    print(f"\n[2/2] Fetching mutual fund NAVs (provider: {MF_PROVIDER}) ...")
    mf = get_mf_provider(MF_PROVIDER)
    bench_provider = get_benchmark_provider(BENCHMARK_PROVIDER)

    navs = mf.get_many(MF_WATCHLIST)
    if not navs:
        print("No MF data fetched — check scheme codes at https://www.mfapi.in")
        return

    metrics = []
    for code, df in navs.items():
        category = df.attrs.get("category", "")
        bench_ticker = benchmark_for_category(category)
        bench = bench_provider.get_history(bench_ticker)
        m = analyze_fund(df, benchmark=bench)
        m["scheme_name"] = df.attrs.get("scheme_name") or MF_WATCHLIST[code]
        m["scheme_code"] = code
        m["category"] = category or "Unknown"
        m["benchmark"] = bench_ticker
        metrics.append(m)

    scored = score_funds(metrics)
    print_mf_report(scored)
    run_ts = record_run("fund", scored, id_col="scheme_code")
    _mf_changes = _collect_changes("fund", scored, "scheme_code", run_ts)
    print_changes("fund", scored, id_col="scheme_code", run_ts=run_ts)
    scored.to_csv("mf_rankings.csv", index=False)
    print("Saved -> mf_rankings.csv")
    _mf_scored = scored


if __name__ == "__main__":
    run_stocks()
    run_mutual_funds()

    if _stock_scored is not None and _mf_scored is not None:
        _report.generate(
            stock_df=_stock_scored,
            mf_df=_mf_scored,
            stock_changes=_stock_changes,
            mf_changes=_mf_changes,
            run_ts=_last_run_ts,
        )

    print(
        "\nDisclaimer: this tool is for your own research/education only. "
        "Scores are relative rankings, not investment advice."
    )
