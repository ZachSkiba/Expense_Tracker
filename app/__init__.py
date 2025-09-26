# app/__init__.py - Updated with FIXED authentication system

from flask import Flask, request, session, redirect, url_for, render_template_string, render_template
from models import db
from config import Config
from app.routes.tracker.recurring import recurring
import datetime
from flask import jsonify

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app.config.from_object(Config)
    
    # Configure session security
    app.config['SESSION_COOKIE_SECURE'] = not app.config['IS_DEVELOPMENT']
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_COOKIE_NAME'] = 'expense_tracker_session'
    
    # Authentication settings
    app.config['LEGACY_AUTH_ENABLED'] = True  # Enable during migration period
    app.config['ADMIN_ACCESS_ENABLED'] = True  # For admin endpoints

    # Initialize extensions
    db.init_app(app)

    # Initialize Flask-Login
    from app.services.auth.auth import init_login_manager
    init_login_manager(app)

    # Process startup recurring payments (this handles missed payments)
    from app.services.tracker.startup_processor import StartupRecurringProcessor
    with app.app_context():
        StartupRecurringProcessor.process_startup_recurring_payments(app)

    # Import auth functions for legacy support
    from app.services.auth.auth import check_legacy_auth

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
        from flask_login import current_user
        
        # Skip auth for static files
        if request.endpoint == 'static':
            return None
            
        # Skip auth for authentication routes
        if request.endpoint and request.endpoint.startswith('auth.'):
            return None
            
        # Skip auth for legacy routes during migration
        if request.endpoint and request.endpoint.startswith('legacy.'):
            return None
            
        # CRITICAL: Skip auth for automation endpoints
        automation_paths = [
            '/admin/health',
            '/admin/recurring/wake-and-process'
        ]
        
        if (request.path in automation_paths or 
            request.endpoint == 'admin.wake_and_process' or
            request.path.endswith('/wake-and-process')):
            print(f"[AUTH_BYPASS] Allowing access to {request.path} (endpoint: {request.endpoint})")
            return None
        
        # Check if user is authenticated with new system
        if current_user.is_authenticated:
            return None
        
        # Check legacy authentication during migration period
        if app.config.get('LEGACY_AUTH_ENABLED') and check_legacy_auth():
            return None
            
        # Redirect to login if not authenticated
        print(f"[AUTH_REQUIRED] Redirecting {request.path} to login")
        return redirect(url_for('auth.login'))

    # Register blueprints
    from app.routes.auth.auth import auth_bp
    from app.routes.dashboard.dashboard import dashboard_bp
    from app.routes.tracker.expenses import expenses_bp
    from app.routes.settings.manage import manage_bp
    from app.routes.tracker.balances import balances_bp
    from app.routes.tracker.settlements import settlements_bp
    from app.routes.tracker.management import management_bp
    from app.routes.admin import admin
    from app.routes.dashboard.groups import groups_bp

    # Register all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    
    # Existing blueprints (may need updates for multi-user)
    app.register_blueprint(management_bp)
    app.register_blueprint(manage_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(balances_bp)
    app.register_blueprint(settlements_bp)
    app.register_blueprint(recurring)
    app.register_blueprint(admin)
    app.register_blueprint(groups_bp)

    # Root route redirect
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.home'))
        else:
            return redirect(url_for('auth.login'))
    
    # BACKUP: Direct route for GitHub Actions (unchanged)
    @app.route('/admin/recurring/wake-and-process', methods=['POST'])
    def backup_wake_and_process():
        """Backup endpoint for GitHub Actions"""
        print("[BACKUP_ROUTE] Direct wake-and-process endpoint called")
        print(f"[BACKUP_ROUTE] User-Agent: {request.headers.get('User-Agent', 'None')}")
        
        try:
            from app.services.tracker.recurring_service import RecurringPaymentService
            from app.services.tracker.startup_processor import StartupRecurringProcessor
            
            # Get request data
            request_data = request.get_json() or {}
            source = request_data.get('source', 'backup_route')
            
            print(f"[BACKUP_ROUTE] Processing triggered by: {source}")
            
            # Run startup processor
            StartupRecurringProcessor.process_startup_recurring_payments(app)
            
            # Run due payments processor
            created_expenses = RecurringPaymentService.process_due_payments()
            
            result = {
                'success': True,
                'message': f'Backup route completed. Created {len(created_expenses)} expenses.',
                'expenses_created': len(created_expenses),
                'source': source,
                'route_type': 'backup_direct_route',
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            print(f"[BACKUP_ROUTE] Completed: {result}")
            return jsonify(result)
            
        except Exception as e:
            print(f"[BACKUP_ROUTE] Error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'route_type': 'backup_direct_route',
                'timestamp': datetime.datetime.now().isoformat()
            }), 500

    return app