# app/routes/auth/auth.py - Updated with email verification and password reset

from flask import Blueprint, request, redirect, url_for, render_template, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Category, db
from app.services.auth.auth import (
    validate_email, validate_password, validate_display_name
)
from app.services.auth.email_service import EmailService
from datetime import datetime
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration route - Updated with email verification"""
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
                    if existing_user.is_active:
                        errors.append("Email already registered")
                    else:
                        errors.append("Email already registered but not verified. Check your email for verification link.")
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
                is_active=False,  # Will be activated after email verification
                created_at=datetime.utcnow()
            )
            user.set_password(password)
            
            # Add user to database
            db.session.add(user)
            db.session.commit()
            
            # Send verification email
            if EmailService.send_verification_email(user):
                flash('Account created successfully! Please check your email and click the verification link to activate your account.', 'success')
            else:
                flash('Account created, but we couldn\'t send the verification email. Please contact support.', 'warning')
            
            return redirect(url_for('auth.verification_sent', email=email))
            
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


@auth_bp.route('/verification-sent')
def verification_sent():
    """Show verification sent page"""
    email = request.args.get('email', '')
    return render_template('auth/verification_sent.html', email=email)


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Handle email verification"""
    if not token:
        flash('Invalid verification link', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Find user with this token
        user = User.query.filter_by(email_verification_token=token).first()
        
        if not user:
            flash('Invalid or expired verification link', 'error')
            return redirect(url_for('auth.login'))
        
        # Verify token is valid and not expired
        if EmailService.verify_token(user, token, 'email_verification'):
            # Activate user account
            EmailService.clear_verification_token(user)
            
            flash('Email verified successfully! You can now sign in to your account.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Verification link has expired. Please sign up again.', 'error')
            # Clean up expired user
            db.session.delete(user)
            db.session.commit()
            return redirect(url_for('auth.signup'))
            
    except Exception as e:
        current_app.logger.error(f"Email verification error: {e}")
        flash('An error occurred during verification. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route - Updated with account verification check"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('auth/login.html')
        
        try:
            # Find user by email
            user = User.query.filter_by(email=email).first()
            
            # Check credentials
            if user and user.check_password(password):
                if not user.is_active:
                    flash('Please verify your email address before signing in. Check your email for the verification link.', 'warning')
                    return render_template('auth/login.html')
                
                # Login successful
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


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('auth/forgot_password.html')
        
        if not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/forgot_password.html')
        
        try:
            # Find user by email
            user = User.query.filter_by(email=email).first()
            
            if user and user.is_active:
                # Send password reset email
                if EmailService.send_password_reset_email(user):
                    flash('Password reset instructions have been sent to your email address.', 'success')
                else:
                    flash('Unable to send password reset email. Please try again later.', 'error')
            else:
                # For security, show same message even if user doesn't exist
                flash('If an account with that email exists, password reset instructions have been sent.', 'info')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Forgot password error: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if not token:
        flash('Invalid password reset link', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Find user with this token
        user = User.query.filter_by(password_reset_token=token).first()
        
        if not user:
            flash('Invalid or expired password reset link', 'error')
            return redirect(url_for('auth.forgot_password'))
        
        # Verify token is valid and not expired
        if not EmailService.verify_token(user, token, 'password_reset'):
            flash('Password reset link has expired. Please request a new one.', 'error')
            return redirect(url_for('auth.forgot_password'))
        
        if request.method == 'POST':
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            errors = []
            
            if not new_password:
                errors.append("New password is required")
            else:
                valid, msg = validate_password(new_password)
                if not valid:
                    errors.append(msg)
            
            if new_password != confirm_password:
                errors.append("Passwords do not match")
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('auth/reset_password.html', token=token)
            
            # Update password
            user.set_password(new_password)
            EmailService.clear_password_reset_token(user)
            
            flash('Password reset successfully! You can now sign in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        
        return render_template('auth/reset_password.html', token=token)
        
    except Exception as e:
        current_app.logger.error(f"Password reset error: {e}")
        flash('An error occurred during password reset. Please try again.', 'error')
        return redirect(url_for('auth.forgot_password'))


@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Resend email verification"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('auth/resend_verification.html')
        
        try:
            user = User.query.filter_by(email=email, is_active=False).first()
            
            if user:
                if EmailService.send_verification_email(user):
                    flash('Verification email sent! Please check your email.', 'success')
                else:
                    flash('Unable to send verification email. Please try again later.', 'error')
            else:
                flash('No unverified account found with that email address.', 'info')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Resend verification error: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('auth/resend_verification.html')


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