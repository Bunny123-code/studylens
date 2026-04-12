"""
backend/utils/feedback.py
Save and retrieve user feedback (helpful / not helpful) for AI results.

Storage: backend/data/feedback.json
Each entry:
{
  "id":        "<uuid>",
  "ip":        "<ip address>",
  "feedback":  "yes" | "no",
  "timestamp": "<ISO 8601 datetime>"
}

If the file does not exist it is created automatically.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Storage location ──────────────────────────────────────────────────────────
_DATA_DIR      = Path(__file__).parent.parent / "data"
_FEEDBACK_FILE = _DATA_DIR / "feedback.json"

_VALID_VALUES = {"yes", "no"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load() -> list:
    """Load all feedback entries from JSON file. Returns [] if missing."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _FEEDBACK_FILE.exists():
        return []
    try:
        with open(_FEEDBACK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.warning("feedback.json is not a list — resetting.")
                return []
            return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read feedback.json: %s. Returning empty list.", exc)
        return []


def _save(entries: list) -> None:
    """Persist all feedback entries to JSON file."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(_FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Could not write feedback.json: %s", exc)
        raise


# ── Public API ────────────────────────────────────────────────────────────────

def save_feedback(ip: str, feedback: str) -> dict:
    """
    Save a feedback entry.

    Args:
        ip:       The client IP address.
        feedback: Must be "yes" or "no".

    Returns:
        The saved entry dict.

    Raises:
        ValueError: If feedback value is not "yes" or "no".
    """
    feedback = str(feedback).strip().lower()
    if feedback not in _VALID_VALUES:
        raise ValueError(
            f"Invalid feedback value '{feedback}'. Must be 'yes' or 'no'."
        )

    entry = {
        "id":        str(uuid.uuid4()),
        "ip":        ip,
        "feedback":  feedback,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    entries = _load()
    entries.append(entry)
    _save(entries)

    logger.info("Feedback saved: id=%s ip=%s value=%s", entry["id"], ip, feedback)
    return entry


def get_all_feedback() -> list:
    """
    Return all feedback entries, most recent first.

    Returns:
        List of feedback entry dicts.
    """
    entries = _load()
    # Sort by timestamp descending (most recent first)
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries
