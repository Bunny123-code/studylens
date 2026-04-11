import os
import json
from flask import Blueprint, request, jsonify
from backend.utils.notes_generator import generate_notes_from_text
from backend.utils.data_loader import load_all_texts

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/generate', methods=['POST'])
def generate_notes():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        notes = generate_notes_from_text(text)
        return jsonify({'notes': notes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notes_bp.route('/from-papers', methods=['POST'])
def from_papers():
    data = request.get_json()
    grade = data.get('grade')
    subject = data.get('subject')
    if not grade or not subject:
        return jsonify({'error': 'Grade and subject required'}), 400
    try:
        texts = load_all_texts(grade=grade, subject=subject)
        combined_text = '\n'.join(texts)
        notes = generate_notes_from_text(combined_text)
        return jsonify({'notes': notes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
