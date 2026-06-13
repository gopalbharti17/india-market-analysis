"""
core/cache.py — A tiny SQLite cache between providers and the network.

Why this matters for scaling:
  * Free APIs rate-limit you; paid APIs charge you. Either way, fetching
    the same fundamentals twice in one day is waste.
  * It makes your runs fast and repeatable during development.

Usage inside any provider:
    cached = cache.get("stock:RELIANCE.NS", max_age_hours=12)
    if cached is None:
        data = <expensive API call>
        cache.set("stock:RELIANCE.NS", data)
"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "market_cache.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, ts REAL, payload TEXT)"
    )
    return conn


def get(key: str, max_age_hours: float = 12.0):
    """Return cached object or None if missing/stale."""
    with _conn() as c:
        row = c.execute("SELECT ts, payload FROM cache WHERE key=?", (key,)).fetchone()
    if row is None:
        return None
    ts, payload = row
    if time.time() - ts > max_age_hours * 3600:
        return None
    return json.loads(payload)


def set(key: str, obj) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO cache (key, ts, payload) VALUES (?,?,?)",
            (key, time.time(), json.dumps(obj, default=str)),
        )


def clear() -> None:
    """Wipe the cache (e.g. force-refresh everything)."""
    with _conn() as c:
        c.execute("DELETE FROM cache")
