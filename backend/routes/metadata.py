from flask import Blueprint, jsonify, request
from backend.utils.data_loader import get_available_subjects, get_available_years

metadata_bp = Blueprint('metadata', __name__)

@metadata_bp.route('/subjects', methods=['GET'])
def subjects():
    """
    Get available subjects for a given board and grade.
    Query params: board, grade
    """
    board = request.args.get('board')
    grade = request.args.get('grade')

    if not board or not grade:
        return jsonify({'error': 'Missing board or grade parameter'}), 400

    try:
        subjects = get_available_subjects(board, grade)
        return jsonify({'subjects': subjects})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@metadata_bp.route('/years', methods=['GET'])
def years():
    """
    Get available years for a given board, grade, and subject.
    Query params: board, grade, subject
    """
    board = request.args.get('board')
    grade = request.args.get('grade')
    subject = request.args.get('subject')

    if not all([board, grade, subject]):
        return jsonify({'error': 'Missing board, grade, or subject parameter'}), 400

    try:
        years = get_available_years(board, grade, subject)
        return jsonify({'years': years})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
