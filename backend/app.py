"""
backend/app.py — StudyLens API Server
Flask application exposing all endpoints.
Run with: python backend/app.py
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

from routes.notes    import notes_bp
from routes.predict  import predict_bp
from routes.metadata import meta_bp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__),   "..", "frontend", "static"),
)
app.secret_key = os.getenv("SECRET_KEY", "studylens-secret-2024")

# Register route blueprints
app.register_blueprint(notes_bp)
app.register_blueprint(predict_bp)
app.register_blueprint(meta_bp)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "StudyLens"})


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
