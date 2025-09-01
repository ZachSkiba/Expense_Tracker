# 3. Update your app/__init__.py to include authentication:

from flask import Flask
from models import db
from config import Config
from app.auth import auth  # Add this import

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

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

    # Apply authentication to all routes
    from app.auth import auth
    
    @app.before_request
    def require_auth():
        from flask import request
        if request.endpoint and request.endpoint.startswith('static'):
            return
        return auth.login_required(lambda: None)()

    # Register blueprints (unchanged)
    from app.routes.expenses import expenses_bp
    from app.routes.users import users_bp
    from app.routes.categories import categories_bp
    from app.routes.manage import manage_bp
    from app.routes.balances import balances_bp
    from app.routes.settlements import settlements_bp

    app.register_blueprint(manage_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(balances_bp)
    app.register_blueprint(settlements_bp)

    return app