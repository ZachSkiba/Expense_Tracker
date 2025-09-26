
# app/auth.py - Authentication helpers and validation (FIXED)

import re
from flask import session
from flask_login import LoginManager

# Shared password for legacy system - CHANGE THIS TO YOUR ACTUAL PASSWORD
SHARED_PASSWORD = "403"

def init_login_manager(app):
    """Initialize Flask-Login"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User  # Import from models (unified)
        return User.query.get(int(user_id))
    
    return login_manager

def check_legacy_auth():
    """Check if user is authenticated with legacy system"""
    return session.get('legacy_authenticated', False)

def legacy_authenticate(password):
    """Check if provided password matches shared password"""
    return password == SHARED_PASSWORD

def validate_email(email):
    """Basic email validation"""
    if not email or len(email.strip()) == 0:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is valid"

def validate_display_name(display_name):
    """Validate display name - FIXED to always return a tuple"""
    if not display_name or len(display_name.strip()) == 0:
        return False, "Display Name is required"
    
    if len(display_name) < 3:
        return False, "Display Name must be at least 3 characters long"
    
    if len(display_name) > 20:
        return False, "Display Name must be less than 20 characters"

    if not re.match(r'^[a-zA-Z0-9_]+$', display_name):
        return False, "Display Name can only contain letters, numbers, and underscores"
    # FIXED: This was missing - always return True for valid display names
    return True, "Display Name is valid"

