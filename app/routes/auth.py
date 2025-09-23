# app/routes/auth.py - Authentication routes (UPDATED - removed username references)

from flask import Blueprint, request, redirect, url_for, render_template, flash, session, current_app
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
            return render_template('auth/signup.html', 
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
    
    return render_template('auth/signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route - Updated for new user model (removed username support)"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('auth/login.html')
        
        try:
            # Find user by email only (removed username support)
            user = User.query.filter_by(email=email).first()
            
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
    
    return render_template('auth/login.html')

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
    """User profile page - Updated to use new template"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile - Updated for full_name, display_name, email"""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        errors = []
        
        # Full name validation
        if not full_name:
            errors.append("Full name is required")
        elif len(full_name) < 2:
            errors.append("Full name must be at least 2 characters")
        elif len(full_name) > 100:
            errors.append("Full name must be less than 100 characters")
        
        # Display name validation
        validate_display_name_result, msg = validate_display_name(display_name)
        if not validate_display_name_result:
            errors.append(msg)

        # Email validation
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
            return render_template('auth/edit_profile.html', user=current_user)
        
        try:
            # Update user information
            current_user.full_name = full_name
            current_user.display_name = display_name
            current_user.email = email
            db.session.commit()
            
            flash('Profile updated successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Profile update integrity error: {e}")
            if 'email' in str(e).lower():
                flash('Email already registered to another account', 'error')
            else:
                flash('Profile update error. Please try again.', 'error')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Profile update error: {e}")
            flash('An error occurred while updating your profile', 'error')
    
    return render_template('auth/edit_profile.html', user=current_user)

@auth_bp.route('/profile/update-field', methods=['POST'])
@login_required
def update_profile_field():
    """Update a single profile field via AJAX"""
    field = request.form.get('field')
    value = request.form.get('value', '').strip()
    
    if not field or not value:
        return {'success': False, 'error': 'Field and value are required'}, 400
    
    try:
        if field == 'full_name':
            # Full name validation
            if len(value) < 2:
                return {'success': False, 'error': 'Full name must be at least 2 characters'}, 400
            elif len(value) > 100:
                return {'success': False, 'error': 'Full name must be less than 100 characters'}, 400
            
            current_user.full_name = value
            
        elif field == 'display_name':
            # Display name validation
            valid, msg = validate_display_name(value)
            if not valid:
                return {'success': False, 'error': msg}, 400
            
            current_user.display_name = value
            
        elif field == 'email':
            # Email validation
            if not validate_email(value):
                return {'success': False, 'error': 'Please enter a valid email address'}, 400
            
            # Check if email is taken by another user
            existing_user = User.query.filter_by(email=value.lower()).first()
            if existing_user and existing_user.id != current_user.id:
                return {'success': False, 'error': 'Email already registered to another account'}, 400
            
            current_user.email = value.lower()
            
        else:
            return {'success': False, 'error': 'Invalid field'}, 400
        
        db.session.commit()
        return {'success': True}
        
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Profile field update integrity error: {e}")
        if 'email' in str(e).lower():
            return {'success': False, 'error': 'Email already registered to another account'}, 400
        elif 'display_name' in str(e).lower():
            return {'success': False, 'error': 'Display name already taken by another user'}, 400
        else:
            return {'success': False, 'error': 'Database error. Please try again.'}, 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile field update error: {e}")
        return {'success': False, 'error': 'An error occurred while updating your profile'}, 500

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
        
        # Check if new password is same as current
        if new_password and current_password and new_password == current_password:
            errors.append("New password must be different from current password")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/change_password.html')
        
        try:
            current_user.set_password(new_password)
            db.session.commit()
            
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Password change error: {e}")
            flash('An error occurred while changing your password', 'error')
    
    return render_template('auth/change_password.html')