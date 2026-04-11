from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.utils.data_loader import load_paper_text
from backend.utils.notes_generator import generate_notes

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/generate', methods=['POST'])
@login_required
def generate():
    data = request.get_json()
    board = data.get('board')
    grade = data.get('grade')
    subject = data.get('subject')
    year = data.get('year')

    if not all([board, grade, subject, year]):
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        text = load_paper_text(board, grade, subject, year)
        notes = generate_notes(text, subject, grade, board)
        return jsonify({'notes': notes})
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to generate notes: {str(e)}'}), 500
