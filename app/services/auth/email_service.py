# app/services/auth/email_service.py - Refactored Email service with template files

import smtplib
import secrets
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, url_for, render_template
from models import db
import os

class EmailService:
    """Handle email verification and password reset functionality"""
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate a cryptographically secure random token"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None):
        """Send an email using SMTP"""
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            from_email = os.getenv('FROM_EMAIL', smtp_username)
            from_name = os.getenv('FROM_NAME', 'Expense Tracker')

            if not smtp_username or not smtp_password:
                current_app.logger.error("SMTP credentials not configured")
                return False

            # Clean Gmail app password (remove spaces/dashes)
            clean_password = smtp_password.replace(' ', '').replace('-', '')

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = to_email

            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if current_app.config.get("FLASK_ENV") == "development":
                    server.set_debuglevel(1)  # show SMTP conversation
                server.starttls()
                server.login(smtp_username, clean_password)
                server.send_message(msg)

            current_app.logger.info(f"✅ Email sent to {to_email}")
            return True

        except Exception as e:
            current_app.logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False

    
    @staticmethod
    def send_verification_email(user):
        """Send email verification to new user"""
        # Generate verification token
        token = EmailService.generate_secure_token()
        expires_at = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
        
        # Store token in user record
        user.email_verification_token = token
        user.email_verification_expires = expires_at
        user.is_active = False  # Deactivate until verified
        db.session.commit()
        
        # Create verification URL
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        
        try:
            # Render HTML template
            html_content = render_template('emails/verification_email.html', 
                                         user=user, 
                                         verification_url=verification_url)
            
            # Text version
            text_content = f"""
WELCOME TO EXPENSE TRACKER

Hello {user.full_name},

Thank you for joining Expense Tracker! We're excited to have you as part of our community.

To complete your registration and secure your account, please verify your email address by visiting the following link:

{verification_url}

IMPORTANT: This verification link will expire in 24 hours.

What you can do with Expense Tracker:
• Track and categorize all your expenses
• Create expense groups with friends and family  
• Set up recurring payments and automated tracking
• Monitor balances and handle settlements
• Generate detailed financial reports

If you didn't create an account with us, you can safely ignore this email.

Welcome aboard!
The Expense Tracker Team

---
This email was sent to {user.email}
Questions? Contact our support team.
            """
            
            # Send email
            success = EmailService.send_email(
                user.email,
                "Welcome! Please verify your email - Expense Tracker",
                html_content,
                text_content
            )
            
            return success
            
        except Exception as e:
            current_app.logger.error(f"Error rendering verification email template: {e}")
            return False
    
    @staticmethod
    def send_password_reset_email(user):
        """Send password reset email to user"""
        # Generate reset token
        token = EmailService.generate_secure_token()
        expires_at = datetime.utcnow() + timedelta(hours=2)  # 2 hour expiry
        
        # Store token in user record
        user.password_reset_token = token
        user.password_reset_expires = expires_at
        db.session.commit()
        
        # Create reset URL
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        try:
            # Render HTML template
            html_content = render_template('emails/password_reset_email.html', 
                                         user=user, 
                                         reset_url=reset_url)
            
            # Text version
            text_content = f"""
PASSWORD RESET REQUEST - EXPENSE TRACKER

Hello {user.full_name},

We received a request to reset the password for your Expense Tracker account.

To reset your password, visit the following link:
{reset_url}

SECURITY NOTICE:
• This link will expire in 2 hours for your security
• If you didn't request this reset, you can safely ignore this email
• Your account remains secure until you complete the reset process

Password Security Tips:
• Use at least 8 characters with letters and numbers
• Choose a unique password for your account
• Consider using a password manager
• Never share your password with anyone

Need help? Contact our support team immediately if you have any security concerns.

Best regards,
The Expense Tracker Security Team

---
This security email was sent to {user.email}
© 2024 Expense Tracker. All rights reserved.
            """
            
            # Send email
            success = EmailService.send_email(
                user.email,
                "Password Reset Request - Expense Tracker",
                html_content,
                text_content
            )
            
            return success
            
        except Exception as e:
            current_app.logger.error(f"Error rendering password reset email template: {e}")
            return False
    
    @staticmethod
    def verify_token(user, token, token_type='email_verification'):
        """Verify a token is valid and not expired"""
        if token_type == 'email_verification':
            stored_token = getattr(user, 'email_verification_token', None)
            expires_at = getattr(user, 'email_verification_expires', None)
        elif token_type == 'password_reset':
            stored_token = getattr(user, 'password_reset_token', None)
            expires_at = getattr(user, 'password_reset_expires', None)
        else:
            return False
        
        # Check token exists and matches
        if not stored_token or not token or stored_token != token:
            return False
        
        # Check expiry
        if not expires_at or datetime.utcnow() > expires_at:
            return False
        
        return True
    
    @staticmethod
    def clear_verification_token(user):
        """Clear email verification token after successful verification"""
        user.email_verification_token = None
        user.email_verification_expires = None
        user.is_active = True
        db.session.commit()
    
    @staticmethod
    def clear_password_reset_token(user):
        """Clear password reset token after successful reset"""
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()