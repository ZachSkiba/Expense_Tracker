from app import create_app
from models import db
import os
import sys

# Set environment based on command line args BEFORE importing config
if '--dev' in sys.argv or '--development' in sys.argv:
    os.environ['ENVIRONMENT'] = 'development'
    print("🔧 DEVELOPMENT mode")
    port = 5001
elif '--prod' in sys.argv or '--production' in sys.argv:
    os.environ['ENVIRONMENT'] = 'production'
    print("🚀 PRODUCTION mode")
    port = 5000
else:
    existing_env = os.environ.get('ENVIRONMENT', 'development')
    os.environ['ENVIRONMENT'] = existing_env
    print(f"📍 {existing_env.upper()} mode")
    port = 5001 if existing_env == "development" else 5000

# Now create the app (this will trigger config loading)
app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # Show which database we're actually using
        from config import Config
        db_info = Config.get_db_info()
        
        print(f"🗄️  Database: {db_info['current_env']} -> {db_info['database_uri'].split('/')[-1]}")
        
        db.create_all()
        print(f"✅ Ready on http://127.0.0.1:{port}")

    app.run(debug=True, port=port, use_reloader=False)