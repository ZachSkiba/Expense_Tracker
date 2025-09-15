# app/routes/auth.py - Authentication routes

from flask import Blueprint, request, redirect, url_for, render_template_string, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Group, Category, db
from app.auth import (
    validate_email, validate_password, validate_username, 
    legacy_authenticate, check_legacy_auth,
    SIGNUP_TEMPLATE, LOGIN_TEMPLATE
)
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not name:
            errors.append("Full name is required")
        elif len(name) < 2:
            errors.append("Full name must be at least 2 characters")
        
        if not username:
            errors.append("Username is required")
        else:
            valid, msg = validate_username(username)
            if not valid:
                errors.append(msg)
            elif User.query.filter_by(username=username).first():
                errors.append("Username already taken")
        
        if not email:
            errors.append("Email is required")
        elif not validate_email(email):
            errors.append("Please enter a valid email address")
        elif User.query.filter_by(email=email).first():
            errors.append("Email already registered")
        
        if not password:
            errors.append("Password is required")
        else:
            valid, msg = validate_password(password)
            if not valid:
                errors.append(msg)
        
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        # If validation fails, show errors
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template_string(SIGNUP_TEMPLATE), 400
        
        try:
            # Create new user
            user = User(
                name=name,
                username=username,
                email=email
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Create default personal categories for the user
            default_categories = [
                'Groceries',
                'Transportation',
                'Rent',
                'Entertainment',
                'Utilities',
                'Healthcare',
                'Other'
            ]
            
            for cat_name in default_categories:
                category = Category(
                    name=cat_name,
                    user_id=user.id,
                    is_default=False
                )
                db.session.add(category)
            
            db.session.commit()
            
            # Log the user in
            login_user(user, remember=False)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome to Expense Tracker, {user.name}!', 'success')
            return redirect(url_for('dashboard.home'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Signup error: {e}")
            flash('An error occurred while creating your account. Please try again.', 'error')
    
    return render_template_string(SIGNUP_TEMPLATE)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    # Check if legacy mode is enabled
    legacy_enabled = current_app.config.get('LEGACY_AUTH_ENABLED', True)
    
    if request.method == 'POST':
        email_or_username = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email_or_username or not password:
            flash('Please enter both email/username and password', 'error')
            return render_template_string(LOGIN_TEMPLATE, legacy_enabled=legacy_enabled)
        
        # Try to find user by email or username
        user = None
        if '@' in email_or_username:
            user = User.query.filter_by(email=email_or_username.lower()).first()
        else:
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
            flash('Invalid email/username or password', 'error')
    
    return render_template_string(LOGIN_TEMPLATE, legacy_enabled=legacy_enabled)

@auth_bp.route('/legacy-login', methods=['POST'])
def legacy_login():
    """Legacy shared password login for migration period"""
    if not current_app.config.get('LEGACY_AUTH_ENABLED', True):
        flash('Legacy login is disabled', 'error')
        return redirect(url_for('auth.login'))
    
    return redirect(url_for('legacy.shared_login'))

@auth_bp.route('/logout')
def logout():
    """Logout route"""
    if current_user.is_authenticated:
        logout_user()
        flash('You have been logged out successfully', 'success')
    
    # Also clear legacy session
    session.pop('authenticated', None)
    
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
        /* Add your CSS styling here */
        body { font-family: Arial, sans-serif; margin: 20px; }
        .profile-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>My Profile</h1>
    <div class="profile-card">
        <h2>{{ user.name }}</h2>
        <p><strong>Username:</strong> {{ user.username }}</p>
        <p><strong>Email:</strong> {{ user.email }}</p>
        <p><strong>Member since:</strong> {{ user.created_at.strftime('%B %d, %Y') }}</p>
        
        <div style="margin-top: 20px;">
            <a href="{{ url_for('auth.edit_profile') }}" class="btn">Edit Profile</a>
            <a href="{{ url_for('auth.change_password') }}" class="btn" style="margin-left: 10px;">Change Password</a>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
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
        body { font-family: Arial, sans-serif; margin: 20px; }
        .form-group { margin-bottom: 15px; }
        .form-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .flash-error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
    </style>
</head>
<body>
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
            <input type="email" name="email" class="form-input" value="{{ user.email }}" required>
        </div>
        
        <button type="submit" class="btn">Update Profile</button>
    </form>
    
    <div style="margin-top: 20px;">
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
        body { font-family: Arial, sans-serif; margin: 20px; }
        .form-group { margin-bottom: 15px; }
        .form-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .flash-error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
    </style>
</head>
<body>
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
    
    <div style="margin-top: 20px;">
        <a href="{{ url_for('auth.profile') }}">&larr; Back to Profile</a>
    </div>
</body>
</html>
'''