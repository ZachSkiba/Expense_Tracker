from flask import Flask
from models import db
from config import Config

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)


    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created/verified")
        except Exception as e:
            print(f"❌ Database error during init: {e}")

    # Register blueprints
    from app.routes.expenses import expenses_bp
    from app.routes.users import users_bp
    from app.routes.categories import categories_bp
    from app.routes.manage import manage_bp
    from app.routes.balances import balances_bp  # NEW
    from app.routes.settlements import settlements_bp  # NEW

    app.register_blueprint(manage_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(balances_bp)  # NEW
    app.register_blueprint(settlements_bp)  # NEW

    return app
