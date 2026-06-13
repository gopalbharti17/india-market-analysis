"""
history_report.py — Query the engine's memory.

Usage:
  python history_report.py stock TCS.NS
  python history_report.py fund 122639
"""

import sys
from core.history import trend

DEFAULT_METRICS = {
    "stock": ["total_score", "quality_score", "growth_score",
              "valuation_score", "momentum_score", "pe", "pledged_pct"],
    "fund": ["total_score", "returns_score", "consistency_score",
             "risk_score", "alpha_3y", "downside_capture"],
}

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("stock", "fund"):
        print(__doc__)
        sys.exit(1)
    kind, entity = sys.argv[1], sys.argv[2]
    df = trend(kind, entity, DEFAULT_METRICS[kind])
    if df.empty:
        print(f"No history yet for {kind} {entity} — run main.py a few times first.")
    else:
        print(f"\nHistory for {kind} {entity} ({len(df)} runs):\n")
        print(df.to_string(index=False))
