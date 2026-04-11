from flask import Blueprint, jsonify
from backend.utils.data_loader import get_available_papers

metadata_bp = Blueprint('metadata', __name__)

@metadata_bp.route('/available')
def available():
    try:
        papers = get_available_papers()
        return jsonify({'papers': papers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
