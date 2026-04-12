"""
backend/utils/rate_limiter.py
Per-IP daily rate limiting stored in a JSON file.

Limits are read from environment variables:
  FREE_DAILY_LIMIT    — default 10
  PREMIUM_DAILY_LIMIT — default 50

Storage: backend/data/rate_limits.json
  {
    "127.0.0.1": {
      "date": "2024-01-15",
      "count": 3,
      "tier": "free"
    }
  }
"""

import os
import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Storage file ─────────────────────────────────────────────────────────────
_DATA_DIR  = Path(__file__).parent.parent / "data"
_LIMITS_FILE = _DATA_DIR / "rate_limits.json"


def _get_limits() -> tuple[int, int]:
    """
    Read FREE_DAILY_LIMIT and PREMIUM_DAILY_LIMIT from environment.
    Falls back to 10 / 50 if not set or invalid.
    """
    try:
        free_limit = int(os.getenv("FREE_DAILY_LIMIT", "10"))
    except ValueError:
        logger.warning("FREE_DAILY_LIMIT env var is not a valid integer. Using default 10.")
        free_limit = 10

    try:
        premium_limit = int(os.getenv("PREMIUM_DAILY_LIMIT", "50"))
    except ValueError:
        logger.warning("PREMIUM_DAILY_LIMIT env var is not a valid integer. Using default 50.")
        premium_limit = 50

    return free_limit, premium_limit


def _load_data() -> dict:
    """Load rate limit records from JSON file. Returns empty dict if missing."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _LIMITS_FILE.exists():
        return {}
    try:
        with open(_LIMITS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read rate_limits.json: %s. Resetting.", exc)
        return {}


def _save_data(data: dict) -> None:
    """Persist rate limit records to JSON file."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(_LIMITS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        logger.error("Could not write rate_limits.json: %s", exc)


def _today() -> str:
    """Return today's date as ISO string (e.g. '2024-01-15')."""
    return date.today().isoformat()


def get_user_tier(ip: str) -> str:
    """
    Return the tier for the given IP address.
    Currently: 'premium' if stored, otherwise 'free'.
    Extend this to check a DB/premium list as needed.
    """
    data = _load_data()
    record = data.get(ip, {})
    return record.get("tier", "free")


def _get_record(ip: str, data: dict) -> dict:
    """
    Return the current record for this IP, resetting count if it is a new day.
    Does NOT mutate the data dict.
    """
    today = _today()
    record = data.get(ip, {})

    # If no record or the stored date is not today, start fresh
    if record.get("date") != today:
        return {
            "date":  today,
            "count": 0,
            "tier":  record.get("tier", "free"),  # preserve tier across days
        }

    return dict(record)


def check_rate_limit(ip: str) -> tuple[bool, int, int]:
    """
    Check whether the given IP is allowed to make another request today.

    Returns:
        (allowed: bool, remaining: int, limit: int)

    'remaining' is the number of requests still available BEFORE this call
    (i.e. if remaining == 0, the request is denied).
    """
    free_limit, premium_limit = _get_limits()
    data   = _load_data()
    record = _get_record(ip, data)

    tier  = record["tier"]
    limit = premium_limit if tier == "premium" else free_limit

    used      = record["count"]
    remaining = max(0, limit - used)
    allowed   = remaining > 0

    return allowed, remaining, limit


def increment_usage(ip: str) -> None:
    """
    Increment the request count for the given IP for today.
    Creates or resets the record as needed.
    """
    data   = _load_data()
    record = _get_record(ip, data)
    record["count"] += 1
    data[ip] = record
    _save_data(data)
    logger.debug("Rate limit incremented for IP %s → count=%d", ip, record["count"])


def set_user_tier(ip: str, tier: str) -> None:
    """
    Explicitly set a user's tier ('free' or 'premium').
    Called by the payment approval flow.
    """
    if tier not in ("free", "premium"):
        raise ValueError(f"Invalid tier '{tier}'. Must be 'free' or 'premium'.")

    data   = _load_data()
    record = _get_record(ip, data)
    record["tier"] = tier
    data[ip] = record
    _save_data(data)
    logger.info("Tier for IP %s set to '%s'.", ip, tier)
