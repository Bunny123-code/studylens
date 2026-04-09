"""
backend/utils/prediction_engine.py
Identifies high-probability exam questions and topics.

Logic:
  1. Topic frequency score (from topic_analyzer)
  2. Recency boost — topics that appeared in the last 1-2 years score higher
  3. Pattern detection — topics skipped for 2+ years are "overdue"
  4. Type weighting — LONG questions in top topics → very likely to repeat
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)

CURRENT_YEAR = date.today().year


def _recency_boost(years: list[str]) -> float:
    """Boost score for topics that appeared recently."""
    int_years = []
    for y in years:
        try:
            int_years.append(int(y))
        except (ValueError, TypeError):
            pass
    if not int_years:
        return 1.0
    latest = max(int_years)
    gap    = CURRENT_YEAR - latest
    # gap=0 → 1.5×, gap=1 → 1.3×, gap=2 → 1.1×, gap≥3 → 1.0×
    if   gap == 0: return 1.5
    elif gap == 1: return 1.3
    elif gap == 2: return 1.1
    else:           return 1.0


def _overdue_flag(years: list[str]) -> bool:
    """Return True if a topic has been absent for 2+ consecutive years."""
    int_years = []
    for y in years:
        try:
            int_years.append(int(y))
        except (ValueError, TypeError):
            pass
    if not int_years:
        return False
    latest = max(int_years)
    return (CURRENT_YEAR - latest) >= 2


def rank_predictions(
    ranked_topics: list[dict],
    questions:     list[dict],
    top_n:         int = 10,
) -> list[dict]:
    """
    Produce a ranked list of "most expected" topics and sample questions.

    Args:
        ranked_topics: Output of topic_analyzer.analyse_topics()["ranked_topics"]
        questions:     Full question list (with 'topic' key set by analyse_topics)
        top_n:         How many top predictions to return.

    Returns:
        List of prediction dicts:
        {
          "topic":           str,
          "probability":     str,   # "Very High" | "High" | "Medium"
          "reason":          str,
          "sample_questions": [ str, ... ]   # up to 3 representative questions
        }
    """
    # Build a quick lookup: topic → list of question texts (prefer LONG)
    q_by_topic: dict[str, list[str]] = {}
    for q in questions:
        topic = q.get("topic", "General / Other")
        q_by_topic.setdefault(topic, []).append((q.get("type", "SHORT"), q["text"]))

    predictions = []
    for entry in ranked_topics[:top_n * 2]:   # consider 2× for filtering
        topic  = entry["topic"]
        score  = entry["score"]
        years  = entry["years"]
        boost  = _recency_boost(years)
        overdue = _overdue_flag(years)

        final_score = score * boost
        if overdue:
            final_score *= 1.4   # overdue topics get extra weight

        # Probability label
        if   final_score >= 20: prob = "Very High"
        elif final_score >= 10: prob = "High"
        else:                   prob = "Medium"

        # Build reason string
        reason_parts = [
            f"Appeared in {len(years)} year(s): {', '.join(years[-3:])}.",
        ]
        if overdue:
            reason_parts.append("Has not appeared recently — likely due.")
        if boost >= 1.3:
            reason_parts.append("Appeared in the last 1-2 years.")

        # Sample questions (prefer LONG, then SHORT, deduplicate)
        qs   = q_by_topic.get(topic, [])
        long_qs  = [t for typ, t in qs if typ == "LONG"]
        short_qs = [t for typ, t in qs if typ == "SHORT"]
        samples  = (long_qs + short_qs)[:3]

        predictions.append({
            "topic":            topic,
            "probability":      prob,
            "final_score":      round(final_score, 2),
            "reason":           " ".join(reason_parts),
            "sample_questions": samples,
        })

    # Sort by final score descending, take top_n
    predictions.sort(key=lambda x: x["final_score"], reverse=True)
    return predictions[:top_n]


def predict_likely_questions(
    questions: list[dict],
    top_n:     int = 5,
) -> list[str]:
    """
    Return up to top_n raw question texts most likely to appear in exams.
    Selects LONG questions from the highest-frequency topics.

    Args:
        questions: Full question list with 'topic' key.
        top_n:     Number of questions to return.

    Returns:
        List of question text strings.
    """
    from collections import Counter

    # Count topic appearances
    topic_counts = Counter(q.get("topic", "General / Other") for q in questions)
    top_topics   = {t for t, _ in topic_counts.most_common(5)}

    # Pick LONG questions from top topics first
    selected = []
    for q in questions:
        if q.get("topic") in top_topics and q.get("type") == "LONG":
            text = q["text"][:300].strip()
            if text and text not in selected:
                selected.append(text)
        if len(selected) >= top_n:
            break

    # If not enough, add SHORT
    if len(selected) < top_n:
        for q in questions:
            if q.get("topic") in top_topics and q.get("type") == "SHORT":
                text = q["text"][:300].strip()
                if text and text not in selected:
                    selected.append(text)
            if len(selected) >= top_n:
                break

    return selected[:top_n]
