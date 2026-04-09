"""
backend/routes/notes.py
POST /generate-notes

Request JSON:
  { "grade": "Grade12", "board": "Federal Board", "subject": "Physics" }

Response JSON:
  {
    "grade": str, "board": str, "subject": str,
    "papers_found": int,
    "notes": { ... }    ← from notes_generator
  }
"""

import logging
from flask import Blueprint, request, jsonify

from utils.data_loader       import load_all_texts
from utils.text_cleaner      import clean_papers
from utils.question_extractor import extract_from_papers
from utils.topic_analyzer    import analyse_topics
from utils.notes_generator   import generate_notes

logger   = logging.getLogger(__name__)
notes_bp = Blueprint("notes", __name__)


@notes_bp.route("/generate-notes", methods=["POST"])
def generate_notes_endpoint():
    body = request.get_json(silent=True) or {}

    grade   = (body.get("grade")   or "").strip()
    board   = (body.get("board")   or "").strip()
    subject = (body.get("subject") or "").strip()

    if not grade or not board or not subject:
        return jsonify({"error": "grade, board, and subject are required."}), 400

    logger.info("Notes request: Grade=%s Board=%s Subject=%s", grade, board, subject)

    # ── Pipeline ──────────────────────────────────────────────────────────────
    try:
        # 1. Load papers
        papers = load_all_texts(grade, board, subject)
        if not papers:
            return jsonify({
                "grade": grade, "board": board, "subject": subject,
                "papers_found": 0,
                "notes": {
                    "summary": (
                        f"No past papers found for {grade} / {board} / {subject}. "
                        "Please add PDF or TXT files to the correct folder."
                    ),
                    "key_topics": [], "definitions": [],
                    "exam_tips": ["Add papers to data/past_papers and retry."],
                    "board_specific_notes": "",
                },
            }), 200

        # 2. Clean text
        cleaned = clean_papers(papers)

        # 3. Extract questions
        questions = extract_from_papers(cleaned)

        # 4. Analyse topics
        analysis = analyse_topics(questions)

        # 5. Generate notes (AI or fallback)
        notes = generate_notes(
            grade, board, subject,
            analysis["ranked_topics"],
            questions,
        )

        return jsonify({
            "grade":        grade,
            "board":        board,
            "subject":      subject,
            "papers_found": len(papers),
            "years_found":  sorted({p["year"] for p in papers if p["year"]}),
            "total_questions_extracted": len(questions),
            "notes":        notes,
        }), 200

    except Exception as exc:
        logger.exception("Error in /generate-notes")
        return jsonify({"error": str(exc)}), 500
