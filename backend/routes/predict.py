from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.utils.prediction_engine import predict_topics
from backend.utils.topic_analyzer import analyze_trends

predict_bp = Blueprint('predict', __name__)

@predict_bp.route('/topics', methods=['POST'])
@login_required
def get_predictions():
    """
    Predict likely exam topics based on past paper analysis.
    Expects JSON: { board, grade, subject, [num_predictions] }
    """
    data = request.get_json()
    board = data.get('board')
    grade = data.get('grade')
    subject = data.get('subject')
    num_predictions = data.get('num_predictions', 5)

    if not all([board, grade, subject]):
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        predictions = predict_topics(board, grade, subject, top_n=num_predictions)
        trends = analyze_trends(board, grade, subject)
        return jsonify({
            'predictions': predictions,
            'trends': trends
        })
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500
