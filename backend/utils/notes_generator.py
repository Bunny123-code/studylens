"""
backend/utils/notes_generator.py
Generates structured exam notes from analysed past-paper content.

Primary:  OpenAI GPT-4o-mini  (fast, affordable)
Fallback: Rule-based extractor (works with NO API key)

Why GPT-4o-mini?
  - Understands educational content natively
  - Produces clean, concise, exam-focused notes
  - Cost-effective (~$0.15 / 1M input tokens as of 2024)
  - Falls back gracefully so the app never crashes
"""

import os
import json
import re
import logging

logger = logging.getLogger(__name__)

# ── OpenAI client (lazy) ──────────────────────────────────────────────────────
_client = None

def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        _client = OpenAI(api_key=api_key)
    return _client


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert Pakistani exam tutor. "
    "Your job is to produce concise, high-yield exam notes from past-paper content. "
    "Focus on what students MUST know to score well. "
    "Be direct. Avoid padding. "
    "Always respond ONLY with valid JSON — no markdown fences, no extra text."
)

NOTES_PROMPT = """\
Grade: {grade}
Board: {board}
Subject: {subject}

Below are the most important questions and topics extracted from {num_years} years of past papers.

TOP TOPICS (by frequency):
{topics_text}

SAMPLE QUESTIONS:
{questions_text}

Generate exam notes in this exact JSON structure:
{{
  "summary": "2-3 sentence overview of what this subject/board emphasises",
  "key_topics": [
    {{
      "topic": "Topic Name",
      "importance": "High | Medium",
      "notes": "3-5 bullet points of must-know content for this topic",
      "likely_question_type": "LONG | SHORT | MCQ"
    }}
  ],
  "definitions": [
    "Term: definition",
    "Term: definition"
  ],
  "exam_tips": [
    "tip 1",
    "tip 2",
    "tip 3"
  ],
  "board_specific_notes": "Any pattern unique to {board} papers"
}}

Return ONLY the JSON object. No markdown. No extra text."""


# ── Fallback notes builder ────────────────────────────────────────────────────

def _fallback_notes(
    grade:         str,
    board:         str,
    subject:       str,
    ranked_topics: list[dict],
    questions:     list[dict],
) -> dict:
    """Generate basic notes without calling the OpenAI API."""
    logger.info("Using fallback notes generator (no AI).")

    key_topics = []
    for t in ranked_topics[:6]:
        topic = t["topic"]
        types = t.get("types", {})
        likely = "LONG" if types.get("LONG", 0) >= types.get("SHORT", 0) else "SHORT"
        key_topics.append({
            "topic": topic,
            "importance": "High" if t["score"] >= 10 else "Medium",
            "notes": (
                f"• Appeared in {t['frequency']} question(s) across {len(t['years'])} year(s).\n"
                f"• Years: {', '.join(t['years'][-4:])}.\n"
                f"• Focus on {likely.lower()}-answer style questions.\n"
                f"• Review past paper questions on this topic carefully.\n"
                f"• Practise writing concise definitions and examples."
            ),
            "likely_question_type": likely,
        })

    # Attempt to pull definitions: "Define X" or "X is defined as"
    defs = []
    for q in questions[:30]:
        text = q["text"]
        m = re.search(r"define\s+([A-Za-z\s]{3,40})", text, re.IGNORECASE)
        if m:
            term = m.group(1).strip().title()
            defs.append(f"{term}: [See past paper {q.get('filename','')}, answer required]")
        if len(defs) >= 5:
            break

    return {
        "summary": (
            f"These notes cover {subject} for {grade} ({board}). "
            f"The most frequently tested topics are: "
            f"{', '.join(t['topic'] for t in ranked_topics[:3])}. "
            f"Focus on these areas to maximise marks."
        ),
        "key_topics": key_topics,
        "definitions": defs or ["No definitions auto-extracted — review textbook glossary."],
        "exam_tips": [
            "Start with the highest-weight questions you are confident about.",
            "In LONG questions, use headings and bullet points — markers reward structure.",
            "Memorise definitions exactly as they appear in the textbook.",
            "Practise the most frequently repeated topics using past papers.",
            f"For {board}: check whether questions tend to be direct or conceptual.",
        ],
        "board_specific_notes": (
            f"{board} papers tend to emphasise "
            f"{ranked_topics[0]['topic'] if ranked_topics else 'core concepts'}. "
            f"Review the last 3 years' papers for pattern recognition."
        ),
        "fallback": True,
    }


# ── AI-powered notes ──────────────────────────────────────────────────────────

def _ai_notes(
    grade:         str,
    board:         str,
    subject:       str,
    ranked_topics: list[dict],
    questions:     list[dict],
) -> dict:
    """Call OpenAI to generate rich notes."""
    client = _get_client()

    # Build topics text (top 8)
    topics_lines = []
    for i, t in enumerate(ranked_topics[:8], 1):
        years_str = ", ".join(t["years"][-4:]) if t["years"] else "?"
        topics_lines.append(
            f"{i}. {t['topic']} — appeared {t['frequency']}× in years: {years_str}"
        )

    # Build sample questions (top 10, LONG first)
    long_qs  = [q["text"][:200] for q in questions if q.get("type") == "LONG"][:6]
    short_qs = [q["text"][:200] for q in questions if q.get("type") == "SHORT"][:4]
    sample_qs = long_qs + short_qs

    # Count distinct years
    years_set = {q.get("year") for q in questions if q.get("year")}

    prompt = NOTES_PROMPT.format(
        grade         = grade,
        board         = board,
        subject       = subject,
        num_years     = len(years_set),
        topics_text   = "\n".join(topics_lines) or "No topics found.",
        questions_text = "\n\n".join(f"- {q}" for q in sample_qs) or "No questions found.",
    )

    response = client.chat.completions.create(
        model       = "gpt-4o-mini",
        messages    = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature = 0.3,
        max_tokens  = 2000,
    )
    raw = response.choices[0].message.content or ""

    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_notes(
    grade:         str,
    board:         str,
    subject:       str,
    ranked_topics: list[dict],
    questions:     list[dict],
) -> dict:
    """
    Generate exam notes. Uses OpenAI if available, falls back to rule-based.

    Args:
        grade:         e.g. "Grade12"
        board:         e.g. "Federal Board"
        subject:       e.g. "Physics"
        ranked_topics: From topic_analyzer.analyse_topics()["ranked_topics"]
        questions:     Full question list with 'topic' key.

    Returns:
        Structured notes dict.
    """
    if not ranked_topics and not questions:
        return {
            "summary": "No past papers found for this selection.",
            "key_topics": [],
            "definitions": [],
            "exam_tips": ["Add past paper files to the data folder and try again."],
            "board_specific_notes": "",
            "error": "no_data",
        }

    try:
        notes = _ai_notes(grade, board, subject, ranked_topics, questions)
        notes["fallback"] = False
        return notes
    except Exception as exc:
        logger.warning("AI notes failed (%s) — using fallback.", exc)
        notes = _fallback_notes(grade, board, subject, ranked_topics, questions)
        notes["ai_error"] = str(exc)
        return notes
