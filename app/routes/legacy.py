# app/routes/legacy.py - Fixed Legacy shared password system

from flask import Blueprint, request, redirect, url_for, render_template, flash, session, current_app
from flask_login import current_user, logout_user

legacy_bp = Blueprint('legacy', __name__, url_prefix='/legacy')

# Set your shared password here
SHARED_PASSWORD = "403"  # Change this to your actual shared password

def legacy_authenticate(password):
    """Check if provided password matches shared password"""
    return password == SHARED_PASSWORD

def check_legacy_auth():
    """Check if user is authenticated with legacy system"""
    return session.get('legacy_authenticated', False)

@legacy_bp.route('/shared-login', methods=['GET', 'POST'])
def shared_login():
    """Legacy shared password login page"""
    # If user is already authenticated with new system, log them out first
    if current_user.is_authenticated:
        logout_user()
    
    # Check if already authenticated with legacy system
    if check_legacy_auth():
        return redirect(url_for('legacy.shared_dashboard'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if legacy_authenticate(password):
            session['legacy_authenticated'] = True
            flash('Logged in with shared access', 'success')
            return redirect(url_for('legacy.shared_dashboard'))
        else:
            flash("Incorrect shared password", 'error')
    
    # Use the existing template from groups/legacy_templates.html
    return render_template("groups/legacy_templates.html")

@legacy_bp.route('/dashboard')
def shared_dashboard():
    """Legacy dashboard - redirect to old expense tracker home"""
    if not check_legacy_auth():
        flash('Please login with shared password', 'error')
        return redirect(url_for('legacy.shared_login'))

    # Redirect to your OLD expense tracker main page
    # Based on your files, it looks like this should be the add expense page
    return redirect(url_for('expenses.add_expense'))

@legacy_bp.route('/logout')
def logout():
    """Legacy logout"""
    session.pop('legacy_authenticated', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))