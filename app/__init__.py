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

    # Add this route directly in your app/__init__.py, before registering blueprints
    @app.route('/emergency-migrate', methods=['GET', 'POST'])
    def emergency_migrate():
        """Emergency database migration - accessible without login"""
        try:
            from sqlalchemy import text
            
            if request.method == 'GET':
                return '''
                <html>
                <body>
                <h2>Emergency Database Migration</h2>
                <p>This will add the missing recurring_payment_id column to your expense table.</p>
                <form method="POST">
                    <button type="submit" style="background: red; color: white; padding: 10px;">
                        RUN MIGRATION (CLICK ONCE)
                    </button>
                </form>
                </body>
                </html>
                '''
            
            # POST request - run migration
            migration_log = []
            
            # Check if recurring_payment table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'recurring_payment'
                );
            """))
            recurring_table_exists = result.scalar()
            
            if not recurring_table_exists:
                migration_log.append("Creating recurring_payment table...")
                db.session.execute(text("""
                    CREATE TABLE recurring_payment (
                        id SERIAL PRIMARY KEY,
                        amount FLOAT NOT NULL,
                        category_id INTEGER NOT NULL REFERENCES category(id),
                        category_description VARCHAR(255),
                        user_id INTEGER NOT NULL REFERENCES "user"(id),
                        frequency VARCHAR(20) NOT NULL,
                        interval_value INTEGER NOT NULL DEFAULT 1,
                        start_date DATE NOT NULL,
                        next_due_date DATE NOT NULL,
                        end_date DATE,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        participant_ids TEXT NOT NULL
                    );
                """))
                migration_log.append("✅ Created recurring_payment table")
            else:
                migration_log.append("✅ recurring_payment table already exists")
            
            # Check if recurring_payment_id column exists in expense table
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'expense' 
                    AND column_name = 'recurring_payment_id'
                );
            """))
            column_exists = result.scalar()
            
            if not column_exists:
                migration_log.append("Adding recurring_payment_id column to expense table...")
                db.session.execute(text("""
                    ALTER TABLE expense 
                    ADD COLUMN recurring_payment_id INTEGER 
                    REFERENCES recurring_payment(id);
                """))
                migration_log.append("✅ Added recurring_payment_id column to expense table")
            else:
                migration_log.append("✅ recurring_payment_id column already exists")
            
            # Commit the changes
            db.session.commit()
            
            return f'''
            <html>
            <body>
            <h2>Migration Complete!</h2>
            <ul>
            {''.join(f'<li>{log}</li>' for log in migration_log)}
            </ul>
            <p><strong>Now you need to:</strong></p>
            <ol>
            <li>Replace your models.py with the full version (uncomment recurring payment code)</li>
            <li>Restart your app</li>
            <li>Remove this emergency migration route</li>
            </ol>
            <a href="/add-expense">Go to App</a>
            </body>
            </html>
            '''
            
        except Exception as e:
            db.session.rollback()
            return f'''
            <html>
            <body>
            <h2>Migration Failed</h2>
            <p>Error: {str(e)}</p>
            <a href="/emergency-migrate">Try Again</a>
            </body>
            </html>
            '''

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