"""Secret loading. Reads .env via python-dotenv and fails fast if a required
secret is missing. Secrets NEVER live in code or the database — only in .env
(gitignored, chmod 600 on the VPS). See summary.md §2 and §7.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load the project-root .env exactly once, on import.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


class MissingSecretError(RuntimeError):
    """Raised when a required environment variable is absent or empty."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise MissingSecretError(
            f"Required secret '{name}' is missing. "
            f"Add it to {_ENV_PATH} (copy from .env.example)."
        )
    return value.strip()


def _optional(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _as_bool(value: str, default: bool = True) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- Alpaca (required) ---
ALPACA_API_KEY: str = _require("ALPACA_API_KEY")
ALPACA_SECRET_KEY: str = _require("ALPACA_SECRET_KEY")
ALPACA_PAPER: bool = _as_bool(_optional("ALPACA_PAPER", "true"), default=True)

# --- SQL Server (required) ---
DB_SERVER: str = _require("DB_SERVER")
DB_NAME: str = _require("DB_NAME")
DB_USER: str = _require("DB_USER")
DB_PASSWORD: str = _require("DB_PASSWORD")
DB_DRIVER: str = _optional("DB_DRIVER", "ODBC Driver 18 for SQL Server")
DB_TRUST_CERT: bool = _as_bool(_optional("DB_TRUST_CERT", "true"), default=True)

# --- Telegram (optional until Phase 9) ---
TELEGRAM_BOT_TOKEN: str = _optional("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str = _optional("TELEGRAM_CHAT_ID")


def telegram_configured() -> bool:
    """True only when both Telegram values are present (checked in Phase 9)."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
