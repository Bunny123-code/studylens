from flask import Blueprint, request, jsonify
from backend.utils.prediction_engine import predict_questions

predict_bp = Blueprint('predict', __name__)

@predict_bp.route('/questions', methods=['POST'])
def predict():
    data = request.get_json()
    subject = data.get('subject')
    grade = data.get('grade')
    if not subject or not grade:
        return jsonify({'error': 'Subject and grade required'}), 400
    try:
        predictions = predict_questions(subject, grade)
        return jsonify({'predictions': predictions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
