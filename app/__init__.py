# 3. Update your app/__init__.py to include authentication:

from flask import Flask, request, session, redirect, url_for, render_template_string
from models import db
from config import Config

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app.config.from_object(Config)
    
    # Configure session security
    app.config['SESSION_COOKIE_SECURE'] = not app.config['IS_DEVELOPMENT']  # HTTPS only in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    app.config['SESSION_PERMANENT'] = False

    
    # Make sessions expire when browser closes
    app.config['SESSION_COOKIE_NAME'] = 'roommate_session'
    # Don't set SESSION_PERMANENT = True (this makes it expire on browser close)

    # Initialize extensions
    db.init_app(app)

    # Import auth functions
    from app.auth import check_auth, authenticate, require_auth, LOGIN_TEMPLATE, SHARED_PASSWORD

    # Security headers
    @app.after_request
    def add_security_headers(response):
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Only allow HTTPS (comment out if not using HTTPS yet)
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Authentication check for all routes
    @app.before_request
    def check_authentication():
        return require_auth()

    # Login route
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            password = request.form.get('password', '')
            if authenticate(password):
                return redirect(url_for('expenses.add_expense'))
            else:
                return render_template_string(LOGIN_TEMPLATE, error="Incorrect password")
        
        # If already authenticated, redirect to main app
        if check_auth():
            return redirect(url_for('expenses.add_expense'))
            
        return render_template_string(LOGIN_TEMPLATE)

    # Logout route
    @app.route('/logout')
    def logout():
        session.pop('authenticated', None)
        return redirect(url_for('login'))

    # Register blueprints (unchanged)
    from app.routes.expenses import expenses_bp
    from app.routes.manage import manage_bp
    from app.routes.balances import balances_bp
    from app.routes.settlements import settlements_bp
    from app.routes.management import management_bp

    app.register_blueprint(manage_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(balances_bp)
    app.register_blueprint(settlements_bp)
    app.register_blueprint(management_bp)

    return app