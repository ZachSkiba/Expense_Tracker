# app/services/auth/email_service.py - Email verification and password reset service

import smtplib
import secrets
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, url_for, render_template_string
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
        
        # Email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 0.9em; color: #666; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>💰 Welcome to Expense Tracker!</h1>
            </div>
            
            <div class="content">
                <h2>Hi {user.full_name},</h2>
                
                <p>Thanks for signing up! We're excited to have you join our community of smart expense trackers.</p>
                
                <p>To complete your registration and activate your account, please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{verification_url}</p>
                
                <div class="warning">
                    <strong>⚠️ Important:</strong> This verification link will expire in 24 hours. If you don't verify within this time, you'll need to sign up again.
                </div>
                
                <p>Once verified, you'll be able to:</p>
                <ul>
                    <li>✅ Create and manage your expenses</li>
                    <li>✅ Join expense tracking groups</li>
                    <li>✅ Set up recurring payments</li>
                    <li>✅ Track balances and settlements</li>
                </ul>
                
                <p>If you didn't create an account with us, you can safely ignore this email.</p>
                
                <p>Happy tracking!<br>The Expense Tracker Team</p>
            </div>
            
            <div class="footer">
                <p>This email was sent to {user.email} because you signed up for Expense Tracker.</p>
                <p>If you have any questions, please contact our support team.</p>
            </div>
        </body>
        </html>
        """
        
        # Text version
        text_content = f"""
        Welcome to Expense Tracker!
        
        Hi {user.full_name},
        
        Thanks for signing up! To complete your registration, please verify your email address by visiting:
        
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create an account with us, you can safely ignore this email.
        
        Best regards,
        The Expense Tracker Team
        """
        
        # Send email
        success = EmailService.send_email(
            user.email,
            "Verify Your Email - Expense Tracker",
            html_content,
            text_content
        )
        
        return success
    
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
        
        # Email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; }}
                .button {{ display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 0.9em; color: #666; }}
                .warning {{ background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; }}
                .security-note {{ background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔒 Password Reset Request</h1>
            </div>
            
            <div class="content">
                <h2>Hi {user.full_name},</h2>
                
                <p>We received a request to reset the password for your Expense Tracker account.</p>
                
                <p>To reset your password, click the button below:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{reset_url}</p>
                
                <div class="warning">
                    <strong>⚠️ Important:</strong> This password reset link will expire in 2 hours for security reasons.
                </div>
                
                <div class="security-note">
                    <strong>🛡️ Security Note:</strong> If you didn't request this password reset, please ignore this email. Your account is secure and no changes have been made.
                </div>
                
                <p>For your security, we recommend choosing a strong password that:</p>
                <ul>
                    <li>Is at least 8 characters long</li>
                    <li>Contains both letters and numbers</li>
                    <li>Is unique to your Expense Tracker account</li>
                </ul>
                
                <p>Best regards,<br>The Expense Tracker Team</p>
            </div>
            
            <div class="footer">
                <p>This email was sent to {user.email} because a password reset was requested.</p>
                <p>If you have any questions, please contact our support team.</p>
            </div>
        </body>
        </html>
        """
        
        # Text version
        text_content = f"""
        Password Reset Request - Expense Tracker
        
        Hi {user.full_name},
        
        We received a request to reset the password for your account.
        
        To reset your password, visit:
        {reset_url}
        
        This link will expire in 2 hours.
        
        If you didn't request this reset, you can safely ignore this email.
        
        Best regards,
        The Expense Tracker Team
        """
        
        # Send email
        success = EmailService.send_email(
            user.email,
            "Reset Your Password - Expense Tracker",
            html_content,
            text_content
        )
        
        return success
    
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