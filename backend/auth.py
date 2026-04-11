from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from backend.models import db, User
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Create initial admin user if not exists
def create_admin_user():
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        hashed = generate_password_hash(os.getenv('ADMIN_PASSWORD', 'admin123'))
        admin = User(username='admin', password_hash=hashed, is_premium=True)
        db.session.add(admin)
        db.session.commit()
