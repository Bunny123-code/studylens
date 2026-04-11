import os
import json
from flask import Flask, send_from_directory, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom modules
from backend.routes.notes import notes_bp
from backend.routes.predict import predict_bp
from backend.routes.metadata import metadata_bp

# ========== NEW IMPORTS FOR AUTH & PAYMENT ==========
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from backend.models import db, User
from backend.auth import auth_bp, create_admin_user
from backend.routes.payment import payment_bp
# ====================================================

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
        if not current_user.is_premium:
            return jsonify({'error': 'Premium subscription required'}), 403
        # Your existing notes generation logic here
        from backend.utils.notes_generator import generate_notes
        data = request.get_json()
        text = data.get('text', '')
        notes = generate_notes(text)
        return jsonify({'notes': notes})

    @app.route('/api/premium/predict-questions', methods=['POST'])
    @login_required
    def premium_predict():
        if not current_user.is_premium:
            return jsonify({'error': 'Premium subscription required'}), 403
        from backend.utils.prediction_engine import predict_questions
        data = request.get_json()
        subject = data.get('subject')
        grade = data.get('grade')
        predictions = predict_questions(subject, grade)
        return jsonify({'predictions': predictions})
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
