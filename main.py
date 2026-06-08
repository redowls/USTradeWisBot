"""USTradeWisBot entrypoint (todo.md Phase 10 / Phase 11 systemd target).

Usage:
  python main.py            # run the live (paper) trading loop
  python main.py --dry-run  # evaluate & size each tick but place no orders / no DB writes
"""

from __future__ import annotations

import sys

from bot import engine


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    engine.run(dry_run=dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
