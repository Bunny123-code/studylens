"""
backend/routes/predict.py
POST /predict-questions

Request JSON:
  { "grade": "Grade12", "board": "Federal Board", "subject": "Physics", "top_n": 10 }

Response JSON:
  {
    "grade": str, "board": str, "subject": str,
    "predictions": [ { topic, probability, reason, sample_questions } ],
    "most_likely_questions": [ str ]
  }
"""

import logging
from flask import Blueprint, request, jsonify

from utils.data_loader        import load_all_texts
from utils.text_cleaner       import clean_papers
from utils.question_extractor import extract_from_papers
from utils.topic_analyzer     import analyse_topics
from utils.prediction_engine  import rank_predictions, predict_likely_questions

logger     = logging.getLogger(__name__)
predict_bp = Blueprint("predict", __name__)


@predict_bp.route("/predict-questions", methods=["POST"])
def predict_questions_endpoint():
    body = request.get_json(silent=True) or {}

    grade   = (body.get("grade")   or "").strip()
    board   = (body.get("board")   or "").strip()
    subject = (body.get("subject") or "").strip()
    top_n   = int(body.get("top_n", 10))

    if not grade or not board or not subject:
        return jsonify({"error": "grade, board, and subject are required."}), 400

    logger.info("Predict request: Grade=%s Board=%s Subject=%s top_n=%d", grade, board, subject, top_n)

    try:
        # 1. Load & clean papers
        papers   = load_all_texts(grade, board, subject)
        if not papers:
            return jsonify({
                "grade": grade, "board": board, "subject": subject,
                "predictions": [],
                "most_likely_questions": [],
                "message": "No past papers found. Add files to data/past_papers.",
            }), 200

        cleaned   = clean_papers(papers)
        questions = extract_from_papers(cleaned)
        analysis  = analyse_topics(questions)

        # 2. Run prediction engine
        predictions     = rank_predictions(
            analysis["ranked_topics"], questions, top_n=top_n
        )
        likely_questions = predict_likely_questions(questions, top_n=5)

        return jsonify({
            "grade":                 grade,
            "board":                 board,
            "subject":               subject,
            "papers_analysed":       len(papers),
            "predictions":           predictions,
            "most_likely_questions": likely_questions,
        }), 200

    except Exception as exc:
        logger.exception("Error in /predict-questions")
        return jsonify({"error": str(exc)}), 500
