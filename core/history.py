"""
core/history.py — The engine's long-term memory.

Every run appends a full snapshot of all scores and metrics to a SQLite
database (research_history.db — separate from the disposable cache; this
file IS your accumulated research record, back it up).

What memory enables:
  * "What changed since last run?" printed automatically with every report
  * Trend queries: how has a fund's downside capture moved over months?
  * Later phases: backtesting needs exactly this kind of longitudinal record.

Storage design: key columns for fast querying (run_ts, kind, entity_id,
total_score) + the full row as JSON, so the schema can evolve without
database migrations.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "research_history.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS score_history (
            run_ts      TEXT NOT NULL,
            kind        TEXT NOT NULL,      -- 'stock' | 'fund'
            entity_id   TEXT NOT NULL,      -- ticker or scheme_code
            name        TEXT,
            total_score REAL,
            rank        INTEGER,
            payload     TEXT NOT NULL       -- full row as JSON
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hist ON score_history (kind, entity_id, run_ts)")
    return conn


def record_run(kind: str, scored: pd.DataFrame, id_col: str) -> str:
    """Append a scored DataFrame as one run snapshot. Returns the run timestamp."""
    run_ts = datetime.now().isoformat(timespec="seconds")
    rows = []
    for rank, (_, r) in enumerate(scored.iterrows(), start=1):
        rows.append((
            run_ts, kind, str(r[id_col]),
            str(r.get("name") or r.get("scheme_name") or ""),
            float(r["total_score"]) if pd.notna(r["total_score"]) else None,
            rank,
            json.dumps({k: (None if pd.isna(v) else v) for k, v in r.items()},
                       default=str),
        ))
    with _conn() as c:
        c.executemany(
            "INSERT INTO score_history VALUES (?,?,?,?,?,?,?)", rows)
    return run_ts


def previous_run(kind: str, before_ts: str) -> pd.DataFrame | None:
    """Latest snapshot strictly before `before_ts`, as a DataFrame."""
    with _conn() as c:
        prev_ts = c.execute(
            "SELECT MAX(run_ts) FROM score_history WHERE kind=? AND run_ts<?",
            (kind, before_ts)).fetchone()[0]
        if prev_ts is None:
            return None
        rows = c.execute(
            "SELECT entity_id, name, total_score, rank, payload FROM score_history "
            "WHERE kind=? AND run_ts=?", (kind, prev_ts)).fetchall()
    df = pd.DataFrame(rows, columns=["entity_id", "name", "total_score", "rank", "payload"])
    df.attrs["run_ts"] = prev_ts
    return df


PILLARS = {
    "stock": ["quality_score", "growth_score", "valuation_score", "momentum_score"],
    "fund": ["returns_score", "consistency_score", "risk_score"],
}


def print_changes(kind: str, current: pd.DataFrame, id_col: str, run_ts: str,
                  min_score_move: float = 5.0):
    """Compare this run to the previous snapshot and narrate what changed."""
    prev = previous_run(kind, run_ts)
    if prev is None:
        print("\n--- (first recorded run — change tracking starts from the next run) ---")
        return

    prev_map = {r.entity_id: r for r in prev.itertuples()}
    prev_payload = {r.entity_id: json.loads(r.payload) for r in prev.itertuples()}
    lines = []

    for rank, (_, cur) in enumerate(current.iterrows(), start=1):
        eid = str(cur[id_col])
        p = prev_map.get(eid)
        if p is None:
            lines.append(f"  NEW: {eid} enters the list at rank {rank}")
            continue

        score_move = (cur["total_score"] or 0) - (p.total_score or 0)
        rank_move = p.rank - rank
        if abs(score_move) >= min_score_move or abs(rank_move) >= 2:
            # find which pillar moved most, to explain WHY
            driver, driver_move = "", 0.0
            for pillar in PILLARS[kind]:
                old = prev_payload[eid].get(pillar)
                new = cur.get(pillar)
                if old is not None and pd.notna(new):
                    move = float(new) - float(old)
                    if abs(move) > abs(driver_move):
                        driver, driver_move = pillar, move
            arrow = "UP" if score_move > 0 else "DOWN"
            why = (f" (driven by {driver.replace('_score','')} "
                   f"{'+' if driver_move>0 else ''}{driver_move:.0f})") if driver else ""
            lines.append(f"  {arrow}: {eid} score {p.total_score:.0f} -> "
                         f"{cur['total_score']:.0f}, rank {p.rank} -> {rank}{why}")

        # governance: newly pledged shares is always worth a line
        old_pl = prev_payload[eid].get("pledged_pct") or 0
        new_pl = cur.get("pledged_pct")
        if pd.notna(new_pl) and float(new_pl or 0) > float(old_pl):
            lines.append(f"  !! FLAG: {eid} promoter pledging rose "
                         f"{old_pl} -> {new_pl}%")

    gone = set(prev_map) - set(str(x) for x in current[id_col])
    for eid in gone:
        lines.append(f"  REMOVED: {eid} (was rank {prev_map[eid].rank})")

    print(f"\n--- CHANGES since last run ({prev.attrs['run_ts']}) ---")
    print("\n".join(lines) if lines else "  No significant changes.")


def trend(kind: str, entity_id: str, metrics: list[str]) -> pd.DataFrame:
    """Time series of chosen metrics for one entity across all recorded runs."""
    with _conn() as c:
        rows = c.execute(
            "SELECT run_ts, payload FROM score_history "
            "WHERE kind=? AND entity_id=? ORDER BY run_ts", (kind, entity_id)).fetchall()
    recs = []
    for ts, payload in rows:
        d = json.loads(payload)
        recs.append({"run_ts": ts, **{m: d.get(m) for m in metrics}})
    return pd.DataFrame(recs)
