# app/routes/auth.py - Authentication routes (FIXED for unified models)

from flask import Blueprint, request, redirect, url_for, render_template_string, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Category, db  # FIXED: Import from unified models
from app.auth import (
    validate_email, validate_password, validate_display_name
)
from datetime import datetime
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration route - Updated for new user model"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        # Get form data and clean it
        full_name = request.form.get('full_name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        # Full name validation
        if not full_name:
            errors.append("Full name is required")
        elif len(full_name) < 2:
            errors.append("Full name must be at least 2 characters")
        
        # Display name validation
        validate_display_name_result, msg = validate_display_name(display_name)
        if not validate_display_name_result:
            errors.append(msg)

        # Email validation
        if not email:
            errors.append("Email is required")
        elif not validate_email(email):
            errors.append("Please enter a valid email address")
        else:
            # Check if email already exists
            try:
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    errors.append("Email already registered")
            except Exception as e:
                current_app.logger.error(f"Database error checking email: {e}")
                errors.append("Database error. Please try again.")
        
        # Password validation
        if not password:
            errors.append("Password is required")
        else:
            valid, msg = validate_password(password)
            if not valid:
                errors.append(msg)
        
        # Confirm password
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        # If validation fails, show errors
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template_string(NEW_SIGNUP_TEMPLATE, 
                                        full_name=full_name,
                                        display_name=display_name,
                                        email=email), 400
        
        # Create new user
        try:
            user = User(
                full_name=full_name,
                display_name=display_name,
                email=email,
                is_active=True,
                created_at=datetime.utcnow()
            )
            user.set_password(password)
            
            # Add user to database
            db.session.add(user)
            db.session.commit()
            
            # Log the user in
            login_user(user, remember=False)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome to Expense Tracker, {user.display_name}! Create your first expense tracker to get started.', 'success')
            return redirect(url_for('dashboard.home'))
            
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Database integrity error during signup: {e}")
            if 'email' in str(e).lower():
                flash('Email already registered', 'error')
            else:
                flash('Registration error. Please try again.', 'error')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Signup error: {e}")
            flash('An error occurred while creating your account. Please try again.', 'error')
    
    return render_template_string(NEW_SIGNUP_TEMPLATE)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route - Updated for new user model"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    # Check if legacy mode is enabled
    legacy_enabled = current_app.config.get('LEGACY_AUTH_ENABLED', True)
    
    if request.method == 'POST':
        email_or_username = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email_or_username or not password:
            flash('Please enter both email and password', 'error')
            return render_template_string(UPDATED_LOGIN_TEMPLATE, legacy_enabled=legacy_enabled)
        
        try:
            # Try to find user by email first (primary method)
            user = User.query.filter_by(email=email_or_username.lower()).first()
            
            # If not found by email and it doesn't contain @, try username (legacy)
            if not user and '@' not in email_or_username:
                user = User.query.filter_by(username=email_or_username).first()
            
            # Check credentials
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=False)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # Redirect to next page if specified, otherwise dashboard
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('dashboard.home'))
            else:
                flash('Invalid email or password', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Login error: {e}")
            flash('Login error. Please try again.', 'error')
    
    return render_template_string(UPDATED_LOGIN_TEMPLATE, legacy_enabled=legacy_enabled)

@auth_bp.route('/logout')
def logout():
    """Logout route"""
    if current_user.is_authenticated:
        logout_user()
        flash('You have been logged out successfully', 'success')
    
    # Also clear legacy session
    session.pop('legacy_authenticated', None)
    
    return redirect(url_for('auth.login'))

# Profile management routes
@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template_string(PROFILE_TEMPLATE, user=current_user)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        errors = []
        
        if not name:
            errors.append("Full name is required")
        elif len(name) < 2:
            errors.append("Full name must be at least 2 characters")
        
        if not email:
            errors.append("Email is required")
        elif not validate_email(email):
            errors.append("Please enter a valid email address")
        elif email != current_user.email:
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                errors.append("Email already registered to another account")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template_string(EDIT_PROFILE_TEMPLATE, user=current_user)
        
        try:
            current_user.name = name
            current_user.email = email
            db.session.commit()
            
            flash('Profile updated successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Profile update error: {e}")
            flash('An error occurred while updating your profile', 'error')
    
    return render_template_string(EDIT_PROFILE_TEMPLATE, user=current_user)

@auth_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        
        if not current_password:
            errors.append("Current password is required")
        elif not current_user.check_password(current_password):
            errors.append("Current password is incorrect")
        
        if not new_password:
            errors.append("New password is required")
        else:
            valid, msg = validate_password(new_password)
            if not valid:
                errors.append(msg)
        
        if new_password != confirm_password:
            errors.append("New passwords do not match")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template_string(CHANGE_PASSWORD_TEMPLATE)
        
        try:
            current_user.set_password(new_password)
            db.session.commit()
            
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Password change error: {e}")
            flash('An error occurred while changing your password', 'error')
    
    return render_template_string(CHANGE_PASSWORD_TEMPLATE)

# Templates for profile management
PROFILE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Profile - Expense Tracker</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .profile-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto; }
        .btn { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px; }
        .btn:hover { background: #0056b3; }
        h1, h2 { color: #2d3748; }
        .back-link { text-align: center; margin-top: 20px; }
        .back-link a { color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="profile-card">
        <h1>My Profile</h1>
        <h2>{{ user.name }}</h2>
        <p><strong>Username:</strong> {{ user.username or 'Not set' }}</p>
        <p><strong>Email:</strong> {{ user.email or 'Not set' }}</p>
        <p><strong>Member since:</strong> {{ user.created_at.strftime('%B %d, %Y') if user.created_at else 'Unknown' }}</p>
        {% if user.last_login %}
        <p><strong>Last login:</strong> {{ user.last_login.strftime('%B %d, %Y at %I:%M %p') }}</p>
        {% endif %}
        
        <div style="margin-top: 20px;">
            <a href="{{ url_for('auth.edit_profile') }}" class="btn">Edit Profile</a>
            {% if user.password_hash %}
            <a href="{{ url_for('auth.change_password') }}" class="btn">Change Password</a>
            {% endif %}
        </div>
    </div>
    
    <div class="back-link">
        <a href="{{ url_for('dashboard.home') }}">&larr; Back to Dashboard</a>
    </div>
</body>
</html>
'''

EDIT_PROFILE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Edit Profile - Expense Tracker</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .form-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto; }
        .form-group { margin-bottom: 15px; }
        .form-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .flash-error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
        h1 { color: #2d3748; margin-bottom: 20px; }
        .back-link { text-align: center; margin-top: 20px; }
        .back-link a { color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>Edit Profile</h1>
        
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="flash-{{ category }}">{{ message }}</div>
        {% endfor %}
        
        <form method="post">
            <div class="form-group">
                <label>Full Name:</label>
                <input type="text" name="name" class="form-input" value="{{ user.name }}" required>
            </div>
            
            <div class="form-group">
                <label>Email:</label>
                <input type="email" name="email" class="form-input" value="{{ user.email or '' }}" required>
            </div>
            
            <button type="submit" class="btn">Update Profile</button>
        </form>
    </div>
    
    <div class="back-link">
        <a href="{{ url_for('auth.profile') }}">&larr; Back to Profile</a>
    </div>
</body>
</html>
'''

CHANGE_PASSWORD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Change Password - Expense Tracker</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .form-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto; }
        .form-group { margin-bottom: 15px; }
        .form-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .flash-error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
        h1 { color: #2d3748; margin-bottom: 20px; }
        .back-link { text-align: center; margin-top: 20px; }
        .back-link a { color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>Change Password</h1>
        
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="flash-{{ category }}">{{ message }}</div>
        {% endfor %}
        
        <form method="post">
            <div class="form-group">
                <label>Current Password:</label>
                <input type="password" name="current_password" class="form-input" required>
            </div>
            
            <div class="form-group">
                <label>New Password:</label>
                <input type="password" name="new_password" class="form-input" required>
            </div>
            
            <div class="form-group">
                <label>Confirm New Password:</label>
                <input type="password" name="confirm_password" class="form-input" required>
            </div>
            
            <button type="submit" class="btn">Change Password</button>
        </form>
    </div>
    
    <div class="back-link">
        <a href="{{ url_for('auth.profile') }}">&larr; Back to Profile</a>
    </div>
</body>
</html>
'''

NEW_SIGNUP_TEMPLATE = '''
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
        .form-container {
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 450px;
        }
        .form-header { text-align: center; margin-bottom: 2rem; }
        .form-title { font-size: 1.875rem; font-weight: bold; color: #1f2937; margin-bottom: 0.5rem; }
        .form-subtitle { color: #6b7280; font-size: 0.875rem; }
        .form-group { margin-bottom: 1rem; }
        .form-label { display: block; font-weight: 500; color: #374151; margin-bottom: 0.5rem; }
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
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        .auth-link { text-align: center; margin-top: 1.5rem; }
        .auth-link a { color: #667eea; text-decoration: none; font-weight: 500; }
        .flash-error { background: #fef2f2; color: #dc2626; padding: 0.75rem; border-radius: 8px; border: 1px solid #fecaca; font-size: 0.875rem; margin-bottom: 1rem; }
        .field-note { font-size: 0.75rem; color: #6b7280; margin-top: 0.25rem; }
    </style>
</head>
<body>
    <div class="form-container">
        <div class="form-header">
            <h1 class="form-title">💰 Join Expense Tracker</h1>
            <p class="form-subtitle">Create your personal account</p>
        </div>
        
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="flash-{{ category }}">{{ message }}</div>
        {% endfor %}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label">Full Name</label>
                <input type="text" name="full_name" class="form-input" placeholder="John Smith" value="{{ full_name or '' }}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Display Name</label>
                <input type="text" name="display_name" class="form-input" placeholder="John" value="{{ display_name or '' }}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-input" placeholder="john@gmail.com" value="{{ email or '' }}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Password</label>
                <input type="password" name="password" class="form-input" required>
            </div>
            <div class="form-group">
                <label class="form-label">Confirm Password</label>
                <input type="password" name="confirm_password" class="form-input" required>
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

UPDATED_LOGIN_TEMPLATE = '''
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
        .form-container {
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
        .form-header { text-align: center; margin-bottom: 2rem; }
        .form-title { font-size: 1.875rem; font-weight: bold; color: #1f2937; margin-bottom: 0.5rem; }
        .form-subtitle { color: #6b7280; font-size: 0.875rem; }
        .form-group { margin-bottom: 1.5rem; }
        .form-label { display: block; font-weight: 500; color: #374151; margin-bottom: 0.5rem; }
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
            margin-bottom: 1rem;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        .btn-secondary {
            background: #6b7280;
        }
        .btn-secondary:hover { background: #4b5563; }
        .auth-link { text-align: center; margin-top: 1.5rem; }
        .auth-link a { color: #667eea; text-decoration: none; font-weight: 500; }
        .flash-error { background: #fef2f2; color: #dc2626; padding: 0.75rem; border-radius: 8px; border: 1px solid #fecaca; font-size: 0.875rem; margin-bottom: 1rem; }
        .legacy-option {
            border-top: 1px solid #e5e7eb;
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            text-align: center;
        }
        .legacy-text {
            color: #6b7280;
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <div class="form-header">
            <h1 class="form-title">💰 Expense Tracker</h1>
            <p class="form-subtitle">Sign in to your account</p>
        </div>
        
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="flash-{{ category }}">{{ message }}</div>
        {% endfor %}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-input" placeholder="Enter your email" required>
            </div>
            <div class="form-group">
                <label class="form-label">Password</label>
                <input type="password" name="password" class="form-input" placeholder="Enter password" required>
            </div>
            <button type="submit" class="btn">Sign In</button>
        </form>
        <div class="auth-link">
            Don't have an account? <a href="{{ url_for('auth.signup') }}">Sign Up</a>
        </div>
    </div>
</body>
</html>
'''