# app/routes/legacy.py - Legacy shared password system for migration

from flask import Blueprint, request, redirect, url_for, render_template, flash, session
from app.auth import legacy_authenticate, check_legacy_auth, SHARED_PASSWORD, LOGIN_TEMPLATE
from flask_login import current_user


legacy_bp = Blueprint('legacy', __name__, url_prefix='/legacy')

@legacy_bp.route('/shared-login', methods=['GET', 'POST'])
def shared_login():
    """Legacy shared password login page"""
    if check_legacy_auth():
        return redirect(url_for('legacy.shared_dashboard'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if legacy_authenticate(password):
            flash('Logged in with shared access', 'success')
            return redirect(url_for('legacy.shared_dashboard'))
        else:
            flash("Incorrect shared password", 'error')
    
    return render_template("groups/legacy_templates.html", page="login", user=current_user)

@legacy_bp.route('/dashboard')
def shared_dashboard():
    """Legacy dashboard for shared access users"""
    if not check_legacy_auth():
        return redirect(url_for('legacy.shared_login'))

    return render_template("groups/dashboard_templates.html", page="dashboard", user=current_user)

@legacy_bp.route('/logout')
def logout():
    """Legacy logout"""
    session.pop('authenticated', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))
