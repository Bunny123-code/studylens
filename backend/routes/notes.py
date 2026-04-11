from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.utils.data_loader import load_papers_texts
from backend.utils.notes_generator import generate_notes

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/generate', methods=['POST'])
@login_required
def generate():
    """
    Generate AI-powered notes from a past paper.
    Expects JSON: { board, grade, subject, year }
    """
    data = request.get_json()
    board = data.get('board')
    grade = data.get('grade')
    subject = data.get('subject')
    year = data.get('year')

    if not all([board, grade, subject, year]):
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        # Load the paper text (concatenated if multiple files exist)
        text = load_papers_texts(board, grade, subject, year)
        if not text:
            return jsonify({'error': 'No paper text found'}), 404

        # Generate notes using OpenAI (or fallback)
        notes = generate_notes(text, subject, grade, board)

        return jsonify({'notes': notes})
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to generate notes: {str(e)}'}), 500
