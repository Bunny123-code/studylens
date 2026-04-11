import os
import json
from flask import Flask, send_from_directory, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Import custom modules
from backend.routes.notes import notes_bp
from backend.routes.predict import predict_bp
from backend.routes.metadata import metadata_bp

# ========== IMPORTS FOR AUTH & PAYMENT ==========
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from backend.models import db, User
from backend.auth import auth_bp, create_admin_user
from backend.routes.payment import payment_bp
# ====================================================

def is_premium_active(user):
    """Check if user has an active premium subscription."""
    if not user.is_premium:
        return False
    if user.subscription_expiry and user.subscription_expiry < datetime.utcnow():
        # Subscription expired – automatically demote
        user.is_premium = False
        db.session.commit()
        return False
    return True

def create_app():
    app = Flask(__name__,
                static_folder='../frontend/static',
                template_folder='../frontend/templates')

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.getenv('DEBUG', 'false').lower() == 'true'

    # ========== DATABASE CONFIGURATION ==========
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    # ===========================================

    CORS(app)

    # ========== FLASK-LOGIN SETUP ==========
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    # =======================================

    # Register existing blueprints
    app.register_blueprint(notes_bp, url_prefix='/api/notes')
    app.register_blueprint(predict_bp, url_prefix='/api/predict')
    app.register_blueprint(metadata_bp, url_prefix='/api/metadata')

    # ========== REGISTER NEW BLUEPRINTS ==========
    app.register_blueprint(auth_bp)
    app.register_blueprint(payment_bp)
    # ============================================

    # Serve frontend static files
    @app.route('/static/<path:path>')
    def serve_static(path):
        return send_from_directory(app.static_folder, path)

    # Main route
    @app.route('/')
    def index():
        return render_template('index.html')

    # API status
    @app.route('/api/status')
    def status():
        return jsonify({
            'status': 'online',
            'message': 'StudyLens API is running'
        })

    # ========== PROTECTED PREMIUM ROUTES ==========
    @app.route('/api/premium/generate-notes', methods=['POST'])
    @login_required
    def premium_generate_notes():
        # Validate premium status with expiry check
        if not is_premium_active(current_user):
            return jsonify({'error': 'Active premium subscription required'}), 403

        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing JSON body'}), 400
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        try:
            from backend.utils.notes_generator import generate_notes
            notes = generate_notes(text)
            return jsonify({'notes': notes})
        except ImportError as e:
            return jsonify({'error': 'Notes generator not available'}), 500
        except Exception as e:
            return jsonify({'error': f'Failed to generate notes: {str(e)}'}), 500

    @app.route('/api/premium/predict-questions', methods=['POST'])
    @login_required
    def premium_predict():
        if not is_premium_active(current_user):
            return jsonify({'error': 'Active premium subscription required'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing JSON body'}), 400
        subject = data.get('subject', '').strip()
        grade = data.get('grade', '').strip()
        if not subject or not grade:
            return jsonify({'error': 'Subject and grade are required'}), 400

        try:
            from backend.utils.prediction_engine import predict_questions
            predictions = predict_questions(subject, grade)
            return jsonify({'predictions': predictions})
        except ImportError as e:
            return jsonify({'error': 'Prediction engine not available'}), 500
        except Exception as e:
            return jsonify({'error': f'Failed to predict questions: {str(e)}'}), 500
    # ==============================================

    # Create tables and admin user on first run
    with app.app_context():
        db.create_all()
        create_admin_user()

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
