# app/auth.py - Enhanced authentication system

from flask import session, request, redirect, url_for, render_template_string, flash, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import User, db
import os
import re

# Initialize Flask-Login
login_manager = LoginManager()

def init_login_manager(app):
    """Initialize Flask-Login with the app"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user callback for Flask-Login"""
    return User.query.get(int(user_id))

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is valid"

def validate_username(username):
    """Validate username format"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 30:
        return False, "Username must be less than 30 characters"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    return True, "Username is valid"

# Legacy support for existing shared password system (for migration period)
SHARED_PASSWORD = os.getenv('SHARED_PASSWORD', '403')

def check_legacy_auth():
    """Check if user is authenticated with legacy system"""
    return session.get('authenticated') == True

def legacy_authenticate(password):
    """Authenticate with legacy shared password"""
    if password == SHARED_PASSWORD:
        session['authenticated'] = True
        session.permanent = False
        return True
    return False

# Templates
SIGNUP_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Sign Up - Expense Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .auth-container {
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            width: 100%;
            max-width: 400px;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-title {
            font-size: 1.875rem;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }
        .auth-subtitle {
            color: #6b7280;
            font-size: 0.875rem;
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        .form-label {
            display: block;
            font-weight: 500;
            color: #374151;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }
        .form-input {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: all 0.2s;
            background: #f9fafb;
        }
        .form-input:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .form-input.error {
            border-color: #ef4444;
            background: #fef2f2;
        }
        .btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.875rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 0.5rem;
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        .btn:active {
            transform: translateY(0);
        }
        .auth-link {
            text-align: center;
            margin-top: 1.5rem;
            font-size: 0.875rem;
            color: #6b7280;
        }
        .auth-link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        .auth-link a:hover {
            text-decoration: underline;
        }
        .flash-messages {
            margin-bottom: 1.5rem;
        }
        .flash-error {
            background: #fef2f2;
            color: #dc2626;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #fecaca;
            font-size: 0.875rem;
        }
        .flash-success {
            background: #f0fdf4;
            color: #16a34a;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #bbf7d0;
            font-size: 0.875rem;
        }
        .password-requirements {
            font-size: 0.75rem;
            color: #6b7280;
            margin-top: 0.25rem;
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="auth-header">
            <h1 class="auth-title">Create Account</h1>
            <p class="auth-subtitle">Start tracking your expenses today</p>
        </div>
        
        <div class="flash-messages">
            {% for category, message in get_flashed_messages(with_categories=true) %}
                <div class="flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        
        <form method="post" novalidate>
            <div class="form-group">
                <label class="form-label" for="name">Full Name</label>
                <input type="text" 
                       id="name" 
                       name="name" 
                       class="form-input" 
                       placeholder="Enter your full name"
                       value="{{ request.form.get('name', '') }}"
                       required>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="username">Username</label>
                <input type="text" 
                       id="username" 
                       name="username" 
                       class="form-input" 
                       placeholder="Choose a username"
                       value="{{ request.form.get('username', '') }}"
                       required>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="email">Email</label>
                <input type="email" 
                       id="email" 
                       name="email" 
                       class="form-input" 
                       placeholder="Enter your email address"
                       value="{{ request.form.get('email', '') }}"
                       required>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="password">Password</label>
                <input type="password" 
                       id="password" 
                       name="password" 
                       class="form-input" 
                       placeholder="Create a password"
                       required>
                <div class="password-requirements">
                    Password must be at least 8 characters with letters and numbers
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="confirm_password">Confirm Password</label>
                <input type="password" 
                       id="confirm_password" 
                       name="confirm_password" 
                       class="form-input" 
                       placeholder="Confirm your password"
                       required>
            </div>
            
            <button type="submit" class="btn">Create Account</button>
        </form>
        
        <div class="auth-link">
            Already have an account? <a href="{{ url_for('auth.login') }}">Sign In</a>
        </div>
    </div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Sign In - Expense Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .auth-container {
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            width: 100%;
            max-width: 400px;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-title {
            font-size: 1.875rem;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }
        .auth-subtitle {
            color: #6b7280;
            font-size: 0.875rem;
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        .form-label {
            display: block;
            font-weight: 500;
            color: #374151;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }
        .form-input {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: all 0.2s;
            background: #f9fafb;
        }
        .form-input:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.875rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 0.5rem;
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        .btn:active {
            transform: translateY(0);
        }
        .btn-secondary {
            background: #f3f4f6;
            color: #374151;
            margin-top: 1rem;
        }
        .btn-secondary:hover {
            background: #e5e7eb;
        }
        .auth-link {
            text-align: center;
            margin-top: 1.5rem;
            font-size: 0.875rem;
            color: #6b7280;
        }
        .auth-link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        .auth-link a:hover {
            text-decoration: underline;
        }
        .flash-messages {
            margin-bottom: 1.5rem;
        }
        .flash-error {
            background: #fef2f2;
            color: #dc2626;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #fecaca;
            font-size: 0.875rem;
        }
        .flash-success {
            background: #f0fdf4;
            color: #16a34a;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #bbf7d0;
            font-size: 0.875rem;
        }
        .divider {
            margin: 1.5rem 0;
            text-align: center;
            position: relative;
        }
        .divider::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 1px;
            background: #e5e7eb;
        }
        .divider span {
            background: white;
            padding: 0 1rem;
            color: #6b7280;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="auth-header">
            <h1 class="auth-title">Welcome Back</h1>
            <p class="auth-subtitle">Sign in to your expense tracker</p>
        </div>
        
        <div class="flash-messages">
            {% for category, message in get_flashed_messages(with_categories=true) %}
                <div class="flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        
        <form method="post" novalidate>
            <div class="form-group">
                <label class="form-label" for="email">Email or Username</label>
                <input type="text" 
                       id="email" 
                       name="email" 
                       class="form-input" 
                       placeholder="Enter your email or username"
                       value="{{ request.form.get('email', '') }}"
                       required
                       autofocus>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="password">Password</label>
                <input type="password" 
                       id="password" 
                       name="password" 
                       class="form-input" 
                       placeholder="Enter your password"
                       required>
            </div>
            
            <button type="submit" class="btn">Sign In</button>
        </form>
        
        {% if legacy_enabled %}
        <div class="divider">
            <span>or</span>
        </div>
        
        <form method="post" action="{{ url_for('auth.legacy_login') }}">
            <button type="submit" class="btn btn-secondary">Continue with Shared Access</button>
        </form>
        {% endif %}
        
        <div class="auth-link">
            Don't have an account? <a href="{{ url_for('auth.signup') }}">Sign Up</a>
        </div>
    </div>
</body>
</html>
'''