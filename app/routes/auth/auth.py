# app/routes/auth/auth.py - Updated without email verification, with security questions

from flask import Blueprint, request, redirect, url_for, render_template, flash, session, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Category, db
from app.services.auth.auth import (
    validate_email, validate_password, validate_display_name
)
from app.services.auth.security_questions import SecurityQuestionsService
from app.services.auth.account_deletion_service import AccountDeletionService
from datetime import datetime
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration route - Updated with security questions (no email verification)"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        # Get form data and clean it
        full_name = request.form.get('full_name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        security_question = request.form.get('security_question', '')
        security_answer = request.form.get('security_answer', '').strip()
        
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
        
        # Security question validation
        if not security_question:
            errors.append("Please select a security question")
        elif not SecurityQuestionsService.validate_question(security_question):
            errors.append("Invalid security question selected")
        
        # Security answer validation
        valid_answer, answer_msg = SecurityQuestionsService.validate_answer(security_answer)
        if not valid_answer:
            errors.append(answer_msg)
        
        # If validation fails, show errors
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/signup.html', 
                                 full_name=full_name,
                                 display_name=display_name,
                                 email=email,
                                 security_question=security_question,
                                 security_questions=SecurityQuestionsService.get_questions()), 400
        
        # Create new user
        try:
            user = User(
                full_name=full_name,
                display_name=display_name,
                email=email,
                is_active=True,  # Immediately active - no email verification
                security_question=security_question,
                created_at=datetime.utcnow()
            )
            user.set_password(password)
            user.set_security_answer(security_answer)
            
            # Add user to database
            db.session.add(user)
            db.session.commit()
            
            # Automatically log in the new user
            login_user(user, remember=False)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Account created successfully! Welcome to Expense Tracker.', 'success')
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
    
    return render_template('auth/signup.html', 
                          security_questions=SecurityQuestionsService.get_questions())


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route - Simplified (no email verification check)"""
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
    """Handle forgot password requests using security questions"""
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
                # Store email in session for security question step
                session['reset_email'] = email
                return redirect(url_for('auth.security_question'))
            else:
                # For security, show same message even if user doesn't exist
                flash('If an account with that email exists, you will be redirected to answer your security question.', 'info')
                return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Forgot password error: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/security-question', methods=['GET', 'POST'])
def security_question():
    """Handle security question for password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    # Check if we have an email in session
    reset_email = session.get('reset_email')
    if not reset_email:
        flash('Please start the password reset process again', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    try:
        user = User.query.filter_by(email=reset_email).first()
        if not user:
            session.pop('reset_email', None)
            flash('Invalid reset session. Please try again.', 'error')
            return redirect(url_for('auth.forgot_password'))
        
        if request.method == 'POST':
            security_answer = request.form.get('security_answer', '').strip()
            
            if not security_answer:
                flash('Please provide an answer to the security question', 'error')
                return render_template('auth/security_question.html', 
                                     question=user.security_question)
            
            # Check security answer
            if user.check_security_answer(security_answer):
                # Store user ID in session for password reset
                session.pop('reset_email', None)
                session['reset_user_id'] = user.id
                return redirect(url_for('auth.reset_password'))
            else:
                flash('Incorrect answer to security question', 'error')
                return render_template('auth/security_question.html', 
                                     question=user.security_question)
        
        return render_template('auth/security_question.html', 
                             question=user.security_question)
        
    except Exception as e:
        current_app.logger.error(f"Security question error: {e}")
        session.pop('reset_email', None)
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('auth.forgot_password'))


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset after security question verification"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    
    # Check if we have a verified user ID in session
    reset_user_id = session.get('reset_user_id')
    if not reset_user_id:
        flash('Please complete the security question verification first', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    try:
        user = User.query.get(reset_user_id)
        if not user:
            session.pop('reset_user_id', None)
            flash('Invalid reset session. Please try again.', 'error')
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
                return render_template('auth/reset_password.html')
            
            # Update password
            user.set_password(new_password)
            db.session.commit()
            
            # Clear reset session
            session.pop('reset_user_id', None)
            
            flash('Password reset successfully! You can now sign in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        
        return render_template('auth/reset_password.html')
        
    except Exception as e:
        current_app.logger.error(f"Password reset error: {e}")
        session.pop('reset_user_id', None)
        flash('An error occurred during password reset. Please try again.', 'error')
        return redirect(url_for('auth.forgot_password'))


@auth_bp.route('/logout')
def logout():
    """Logout route"""
    if current_user.is_authenticated:
        logout_user()
        flash('You have been logged out successfully', 'success')
    
    # Also clear legacy session and any reset sessions
    session.pop('legacy_authenticated', None)
    session.pop('reset_email', None)
    session.pop('reset_user_id', None)
    
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

@auth_bp.route('/profile/update-security-question', methods=['GET', 'POST'])
@login_required
def update_security_question():
    """Update user's security question and answer"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_question = request.form.get('security_question', '')
        new_answer = request.form.get('security_answer', '').strip()
        
        errors = []
        
        # Verify current password
        if not current_password:
            errors.append("Current password is required")
        elif not current_user.check_password(current_password):
            errors.append("Current password is incorrect")
        
        # Validate security question
        if not new_question:
            errors.append("Please select a security question")
        elif not SecurityQuestionsService.validate_question(new_question):
            errors.append("Invalid security question selected")
        
        # Validate security answer
        valid_answer, answer_msg = SecurityQuestionsService.validate_answer(new_answer)
        if not valid_answer:
            errors.append(answer_msg)
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/update_security_question.html',
                                 security_questions=SecurityQuestionsService.get_questions(),
                                 current_question=current_user.security_question)
        
        try:
            # Update security question and answer
            current_user.security_question = new_question
            current_user.set_security_answer(new_answer)
            db.session.commit()
            
            flash('Security question updated successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Security question update error: {e}")
            flash('An error occurred while updating your security question', 'error')
    
    return render_template('auth/update_security_question.html',
                         security_questions=SecurityQuestionsService.get_questions(),
                         current_question=current_user.security_question)

@auth_bp.route('/profile/delete-account-check', methods=['GET'])
@login_required
def delete_account_check():
    """Check account deletion eligibility and show preview"""
    eligibility = AccountDeletionService.check_deletion_eligibility(current_user)
    
    return jsonify(eligibility)

@auth_bp.route('/profile/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account with all associated logic"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Check confirmation
        confirmation = data.get('confirmation', '').strip().lower()
        if confirmation != 'delete my account':
            return jsonify({
                'success': False, 
                'error': 'Please type "delete my account" to confirm'
            }), 400
        
        # Perform deletion
        success, message = AccountDeletionService.delete_user_account(current_user)
        
        if success:
            # Log out the user since account is deleted
            logout_user()
            return jsonify({
                'success': True,
                'message': message,
                'redirect_url': url_for('auth.login')
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"Account deletion error: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while deleting your account'
        }), 500