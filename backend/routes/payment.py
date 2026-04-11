from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from backend.models import db, PaymentRequest
import random
import string
import os

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

def generate_reference():
    prefix = "SL"
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{suffix}"

@payment_bp.route('/subscribe')
@login_required
def subscribe():
    return render_template('subscribe.html',
                         bank_name=os.getenv('BANK_NAME'),
                         account_name=os.getenv('ACCOUNT_NAME'),
                         account_number=os.getenv('ACCOUNT_NUMBER'),
                         price=int(os.getenv('PRICE_PKR', 500)))

@payment_bp.route('/create', methods=['POST'])
@login_required
def create_request():
    plan = request.form.get('plan', 'monthly')
    amount = int(os.getenv('PRICE_PKR', 500))
    ref = generate_reference()
    while PaymentRequest.query.filter_by(reference_code=ref).first():
        ref = generate_reference()

    payment_req = PaymentRequest(
        user_id=current_user.id,
        reference_code=ref,
        amount=amount,
        plan=plan
    )
    db.session.add(payment_req)
    db.session.commit()

    return render_template('payment_instructions.html',
                         reference=ref,
                         amount=amount,
                         bank_name=os.getenv('BANK_NAME'),
                         account_name=os.getenv('ACCOUNT_NAME'),
                         account_number=os.getenv('ACCOUNT_NUMBER'),
                         iban=os.getenv('IBAN'))

@payment_bp.route('/status')
@login_required
def payment_status():
    pending = PaymentRequest.query.filter_by(user_id=current_user.id, status='pending').first()
    if pending and pending.status == 'completed':
        return jsonify({'status': 'completed'})
    return jsonify({'status': 'pending'})
