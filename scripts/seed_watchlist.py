"""Seed the watchlist table with the default liquid symbols (config.DEFAULT_WATCHLIST).

Idempotent — re-running reactivates existing rows rather than duplicating.
Run from the project root:  python -m scripts.seed_watchlist
"""

from __future__ import annotations

from bot import config, db


def main() -> None:
    for symbol, name in config.DEFAULT_WATCHLIST:
        db.upsert_watchlist_symbol(symbol, name)
    active = db.get_active_watchlist()
    print(f"Seeded watchlist. {len(active)} active symbols:")
    print("  " + ", ".join(row["symbol"] for row in active))


if __name__ == "__main__":
    main()
