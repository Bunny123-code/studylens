"""
backend/utils/question_extractor.py
Extracts and classifies questions from cleaned past-paper text.

Question types identified:
  - MCQ     : multiple-choice (options a/b/c/d present)
  - SHORT   : numbered short-answer questions (1–5 lines)
  - LONG    : essay / detailed questions (6+ lines or marks ≥ 5)

Output per question:
  {
    "text":   str,   # full question text
    "type":   str,   # "MCQ" | "SHORT" | "LONG"
    "marks":  int | None,
    "number": int | None,
  }
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Patterns ──────────────────────────────────────────────────────────────────

# Matches "Q.1", "Q1.", "1.", "1)", "(1)", "Question 1"
_Q_START = re.compile(
    r"(?:^|\n)"                            # start of line
    r"(?:Q(?:uestion)?\.?\s*)?(\d{1,2})"  # optional Q prefix + number
    r"[\.\):]?\s+",                        # separator
    re.IGNORECASE,
)

# MCQ option line: "(a)", "a)", "A.", "A -"
_MCQ_OPTION = re.compile(
    r"^\s*[\(\[]?[abcdABCD][\)\]\.:\-]\s+\S",
    re.MULTILINE,
)

# Marks indicator: "(5 marks)", "[3 marks]", "5 Marks"
_MARKS_RE = re.compile(
    r"[\[\(]?\s*(\d+)\s*marks?\s*[\]\)]?",
    re.IGNORECASE,
)

# "Define", "Explain", "Describe", "Prove", "Derive" → likely LONG
_LONG_VERBS = re.compile(
    r"\b(explain|describe|prove|derive|discuss|elaborate|evaluate|compare|analyse|analyze)\b",
    re.IGNORECASE,
)

# "Define", "State", "Name", "List", "Write" → likely SHORT
_SHORT_VERBS = re.compile(
    r"\b(define|state|name|list|write|give|identify|calculate|find|solve|what is|what are)\b",
    re.IGNORECASE,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_marks(text: str) -> int | None:
    m = _MARKS_RE.search(text)
    return int(m.group(1)) if m else None


def _classify(text: str, marks: int | None) -> str:
    # MCQ: has option lines
    if _MCQ_OPTION.search(text):
        return "MCQ"
    # LONG: explicit marks ≥ 5, or long-answer verbs, or very long text
    if (marks and marks >= 5) or _LONG_VERBS.search(text) or len(text.split()) > 80:
        return "LONG"
    # Default SHORT
    return "SHORT"


def _split_into_blocks(text: str) -> list[str]:
    """Split paper text into question-sized blocks by question numbering."""
    positions = [m.start() for m in _Q_START.finditer(text)]
    if not positions:
        # Fallback: split on blank lines (paragraph mode)
        return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]

    blocks = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        blocks.append(text[pos:end].strip())
    return blocks


# ── Public API ────────────────────────────────────────────────────────────────

def extract_questions(text: str) -> list[dict]:
    """
    Extract all questions from one paper's cleaned text.

    Args:
        text: Cleaned paper text.

    Returns:
        List of question dicts with keys: text, type, marks, number.
    """
    blocks    = _split_into_blocks(text)
    questions = []

    for i, block in enumerate(blocks, start=1):
        if len(block.split()) < 3:   # skip tiny fragments
            continue
        marks  = _extract_marks(block)
        q_type = _classify(block, marks)
        questions.append({
            "text":   block,
            "type":   q_type,
            "marks":  marks,
            "number": i,
        })

    logger.info("Extracted %d questions from text block.", len(questions))
    return questions


def extract_from_papers(papers: list[dict]) -> list[dict]:
    """
    Run extract_questions() on every paper and attach paper metadata.

    Args:
        papers: List of cleaned paper dicts (filename, year, text).

    Returns:
        Flat list of question dicts, each with 'filename' and 'year' added.
    """
    all_questions = []
    for paper in papers:
        qs = extract_questions(paper["text"])
        for q in qs:
            all_questions.append({
                **q,
                "filename": paper["filename"],
                "year":     paper["year"],
            })
    logger.info("Total questions extracted: %d", len(all_questions))
    return all_questions
