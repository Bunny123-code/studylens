"""
app.py — StudyLens SaaS Main Application
Full-featured Flask app: OCR + AI + Payments + Admin + Rate Limiting + Caching
"""

import os
import uuid
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from functools import wraps

from utils.ocr import extract_text
from utils.ai_processor import process_text
from utils.rate_limiter import check_rate_limit, increment_usage, get_user_tier
from utils.cache import get_cached_result, cache_result
from utils.payment import save_payment_submission, get_all_submissions, approve_user, reject_user

# ── Load environment ─────────────────────────────────────────────────────────
load_dotenv()

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(32).hex())
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB per file

BASE_DIR       = os.path.dirname(__file__)
UPLOAD_FOLDER  = os.path.join(BASE_DIR, "uploads")
PAYMENT_FOLDER = os.path.join(BASE_DIR, "payment_screenshots")
DATA_FOLDER    = os.path.join(BASE_DIR, "data")

for folder in [UPLOAD_FOLDER, PAYMENT_FOLDER, DATA_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config["UPLOAD_FOLDER"]  = UPLOAD_FOLDER
app.config["PAYMENT_FOLDER"] = PAYMENT_FOLDER

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "tiff"}
ALLOWED_PAYMENT_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def allowed_payment_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PAYMENT_EXTENSIONS


def get_client_ip() -> str:
    """Get real client IP, handling proxies."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    return request.remote_addr or "unknown"


def admin_required(f):
    """Decorator: require admin session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ── Routes: Main ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """
    Handle multi-file upload.
    1. Validate files
    2. Check rate limit
    3. Run OCR on each image
    4. Merge text
    5. Check cache
    6. AI process
    7. Return results
    """
    ip = get_client_ip()

    # ── Rate limit check ─────────────────────────────────────────────────────
    allowed, remaining, limit = check_rate_limit(ip)
    if not allowed:
        return jsonify({
            "error": (
                f"You've reached your daily limit of {limit} requests. "
                "Upgrade to Premium for 50 requests/day."
            ),
            "rate_limited": True,
            "remaining": 0,
            "limit": limit,
        }), 429

    # ── File validation ──────────────────────────────────────────────────────
    files = request.files.getlist("images")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files selected. Please upload at least one image."}), 400

    valid_files = [f for f in files if f and f.filename and allowed_image(f.filename)]
    if not valid_files:
        return jsonify({
            "error": (
                f"Invalid file type(s). Allowed formats: "
                f"{', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS)).upper()}."
            )
        }), 415

    if len(valid_files) > 10:
        return jsonify({"error": "Maximum 10 images per request."}), 400

    # ── Save files temporarily ───────────────────────────────────────────────
    saved_paths = []
    try:
        for f in valid_files:
            ext = secure_filename(f.filename).rsplit(".", 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            save_path = os.path.join(UPLOAD_FOLDER, unique_name)
            f.save(save_path)
            saved_paths.append(save_path)
            logger.info("Saved: %s", save_path)
    except Exception as exc:
        logger.exception("Failed to save files.")
        _cleanup(saved_paths)
        return jsonify({"error": f"Could not save uploaded files: {exc}"}), 500

    try:
        # ── OCR: extract text from each image ────────────────────────────────
        all_texts = []
        ocr_errors = []
        for path in saved_paths:
            try:
                text = extract_text(path)
                if text and text.strip():
                    all_texts.append(text.strip())
            except ValueError as ve:
                ocr_errors.append(str(ve))
                logger.warning("OCR failed for %s: %s", path, ve)

        if not all_texts:
            error_detail = " | ".join(ocr_errors) if ocr_errors else "No readable text found."
            return jsonify({
                "error": (
                    "No readable text was found in the uploaded image(s). "
                    "Please upload clearer images of textbook pages or question papers. "
                    f"Details: {error_detail}"
                )
            }), 422

        # ── Merge all OCR text ────────────────────────────────────────────────
        combined_text = "\n\n--- Page Break ---\n\n".join(all_texts)
        logger.info("Total OCR characters: %d from %d image(s)", len(combined_text), len(all_texts))

        # ── Cache check ───────────────────────────────────────────────────────
        cached = get_cached_result(combined_text)
        if cached:
            logger.info("Cache hit — returning cached result.")
            increment_usage(ip)
            cached["cached"] = True
            cached["remaining"] = remaining - 1
            cached["limit"] = limit
            return jsonify(cached), 200

        # ── AI processing ─────────────────────────────────────────────────────
        result = process_text(combined_text)

        # ── Cache result ──────────────────────────────────────────────────────
        cache_result(combined_text, result)

        # ── Increment usage ───────────────────────────────────────────────────
        increment_usage(ip)

        result["cached"] = False
        result["remaining"] = remaining - 1
        result["limit"] = limit
        return jsonify(result), 200

    except ValueError as ve:
        logger.warning("ValueError: %s", ve)
        return jsonify({"error": str(ve)}), 422

    except Exception as exc:
        logger.exception("Unexpected error.")
        return jsonify({"error": f"An unexpected error occurred: {exc}"}), 500

    finally:
        _cleanup(saved_paths)


def _cleanup(paths: list[str]):
    """Delete temporary files."""
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
                logger.info("Cleaned up: %s", p)
        except Exception as e:
            logger.warning("Could not delete %s: %s", p, e)


# ── Routes: Payment ───────────────────────────────────────────────────────────
@app.route("/payment-info")
def payment_info():
    """Return bank details for payment."""
    bank_name    = os.getenv("BANK_NAME", "Meezan Bank")
    account_name = os.getenv("ACCOUNT_NAME", "StudyLens Pakistan")
    account_no   = os.getenv("ACCOUNT_NUMBER", "XXXX-XXXX-XXXX")
    iban         = os.getenv("IBAN", "PK00MEZN0000000000000000")
    price        = os.getenv("PRICE_PKR", "500")

    return jsonify({
        "bank_name":    bank_name,
        "account_name": account_name,
        "account_no":   account_no,
        "iban":         iban,
        "price_pkr":    price,
        "instructions": (
            f"Transfer Rs. {price}/month to the above account. "
            "Take a screenshot and upload it below."
        ),
    })


@app.route("/submit-payment", methods=["POST"])
def submit_payment():
    """Handle payment screenshot submission."""
    ip = get_client_ip()

    if "screenshot" not in request.files:
        return jsonify({"error": "No screenshot uploaded."}), 400

    screenshot = request.files["screenshot"]
    if not screenshot or screenshot.filename == "":
        return jsonify({"error": "Please upload a payment screenshot."}), 400

    if not allowed_payment_file(screenshot.filename):
        return jsonify({"error": "Screenshot must be PNG, JPG, JPEG, or PDF."}), 415

    # Save screenshot
    ext = secure_filename(screenshot.filename).rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(PAYMENT_FOLDER, filename)

    try:
        screenshot.save(save_path)
    except Exception as exc:
        return jsonify({"error": f"Could not save screenshot: {exc}"}), 500

    # Store submission record
    whatsapp = request.form.get("whatsapp", "").strip()
    note     = request.form.get("note", "").strip()

    save_payment_submission(ip, filename, whatsapp, note)

    return jsonify({
        "success": True,
        "message": (
            "Payment screenshot submitted! "
            "Your account will be upgraded within 24 hours after verification."
        ),
    }), 200


# ── Routes: Admin ─────────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        admin_pw = os.getenv("ADMIN_PASSWORD", "admin123")
        if password == admin_pw:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        flash("Incorrect password.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_panel():
    submissions = get_all_submissions()
    return render_template("admin.html", submissions=submissions)


@app.route("/admin/approve/<submission_id>", methods=["POST"])
@admin_required
def admin_approve(submission_id):
    ok = approve_user(submission_id)
    if ok:
        return jsonify({"success": True, "message": "User approved."})
    return jsonify({"error": "Submission not found."}), 404


@app.route("/admin/reject/<submission_id>", methods=["POST"])
@admin_required
def admin_reject(submission_id):
    ok = reject_user(submission_id)
    if ok:
        return jsonify({"success": True, "message": "Submission rejected."})
    return jsonify({"error": "Submission not found."}), 404


@app.route("/api/status")
def api_status():
    """Return current user's rate limit status."""
    ip = get_client_ip()
    allowed, remaining, limit = check_rate_limit(ip)
    tier = get_user_tier(ip)
    return jsonify({
        "ip": ip,
        "tier": tier,
        "remaining": remaining,
        "limit": limit,
        "allowed": allowed,
    })


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", "5000"))
    logger.info("StudyLens starting on port %d (debug=%s)", port, debug_mode)
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
