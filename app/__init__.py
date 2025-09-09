# app/__init__.py - Simplified without scheduler

from flask import Flask, request, session, redirect, url_for, render_template_string, render_template
from models import db
from config import Config
from app.routes.recurring import recurring

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app.config.from_object(Config)
    
    # Configure session security
    app.config['SESSION_COOKIE_SECURE'] = not app.config['IS_DEVELOPMENT']
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_COOKIE_NAME'] = 'roommate_session'
    
    # Admin access for manual processing
    app.config['ADMIN_ACCESS_ENABLED'] = True

    # Initialize extensions
    db.init_app(app)

    # Process startup recurring payments (this handles missed payments)
    from app.startup_processor import StartupRecurringProcessor
    with app.app_context():
        StartupRecurringProcessor.process_startup_recurring_payments(app)

    # Import auth functions
    from app.auth import check_auth, authenticate, require_auth, LOGIN_TEMPLATE, SHARED_PASSWORD

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Authentication check for all routes
    @app.before_request
    def check_authentication():
        # Allow specific admin endpoints to bypass auth for automation
        if request.endpoint and (
            request.path == '/admin/recurring/wake-and-process' or
            request.path == '/admin/health'
        ):
            return None
        return require_auth()

    # Login/logout routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            password = request.form.get('password', '')
            if authenticate(password):
                return redirect(url_for('expenses.add_expense'))
            else:
                return render_template_string(LOGIN_TEMPLATE, error="Incorrect password")
        
        if check_auth():
            return redirect(url_for('expenses.add_expense'))
            
        return render_template_string(LOGIN_TEMPLATE)

    @app.route('/logout')
    def logout():
        session.pop('authenticated', None)
        return redirect(url_for('login'))

    # Register blueprints
    from app.routes.expenses import expenses_bp
    from app.routes.manage import manage_bp
    from app.routes.balances import balances_bp
    from app.routes.settlements import settlements_bp
    from app.routes.management import management_bp
    from app.routes.admin import admin

    app.register_blueprint(manage_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(balances_bp)
    app.register_blueprint(settlements_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(recurring)
    app.register_blueprint(admin)

    return app