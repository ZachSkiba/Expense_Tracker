# app/__init__.py - Final version with proper auth bypass

from flask import Flask, request, session, redirect, url_for, render_template_string, render_template
from models import db
from config import Config
from app.routes.recurring import recurring
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

    
    # Make sessions expire when browser closes
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

    # Authentication check for all routes - CRITICAL FIX
    @app.before_request
    def check_authentication():
        # Skip auth for static files
        if request.endpoint == 'static':
            return None
            
        # Skip auth for login page
        if request.endpoint == 'login':
            return None
            
        # CRITICAL: Skip auth for automation endpoints - check path AND endpoint
        automation_paths = [
            '/admin/health',
            '/admin/recurring/wake-and-process'
        ]
        
        # Check both path and endpoint for wake-and-process
        if (request.path in automation_paths or 
            request.endpoint == 'admin.wake_and_process' or
            request.path.endswith('/wake-and-process')):
            print(f"[AUTH_BYPASS] Allowing access to {request.path} (endpoint: {request.endpoint})")
            return None
            
        # Require auth for everything else
        if not check_auth():
            print(f"[AUTH_REQUIRED] Redirecting {request.path} to login")
            return redirect(url_for('login'))
        
        return None

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

    
    
    # BACKUP: Direct route for GitHub Actions
    @app.route('/admin/recurring/wake-and-process', methods=['POST'])
    def backup_wake_and_process():
        """Backup endpoint for GitHub Actions"""
        print("[BACKUP_ROUTE] Direct wake-and-process endpoint called")
        print(f"[BACKUP_ROUTE] User-Agent: {request.headers.get('User-Agent', 'None')}")
        
        try:
            from app.services.recurring_service import RecurringPaymentService
            from app.startup_processor import StartupRecurringProcessor
            
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