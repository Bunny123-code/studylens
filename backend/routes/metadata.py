"""
backend/routes/metadata.py
GET /metadata                  → all grades, boards, subjects
GET /metadata/grades           → list of grades
GET /metadata/boards?grade=X   → boards for a grade
GET /metadata/subjects?grade=X&board=Y → subjects
"""

import logging
from flask import Blueprint, request, jsonify
from utils.data_loader import list_grades, list_boards, list_subjects

logger  = logging.getLogger(__name__)
meta_bp = Blueprint("metadata", __name__)


@meta_bp.route("/metadata")
def all_metadata():
    grades = list_grades()
    result = {}
    for g in grades:
        result[g] = {}
        for b in list_boards(g):
            result[g][b] = list_subjects(g, b)
    return jsonify(result)


@meta_bp.route("/metadata/grades")
def get_grades():
    return jsonify(list_grades())


@meta_bp.route("/metadata/boards")
def get_boards():
    grade = request.args.get("grade", "").strip()
    if not grade:
        return jsonify({"error": "grade param required"}), 400
    return jsonify(list_boards(grade))


@meta_bp.route("/metadata/subjects")
def get_subjects():
    grade = request.args.get("grade", "").strip()
    board = request.args.get("board", "").strip()
    if not grade or not board:
        return jsonify({"error": "grade and board params required"}), 400
    return jsonify(list_subjects(grade, board))
