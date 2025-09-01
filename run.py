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
    # Check if we're on Render (has RENDER environment variable)
    if os.environ.get('RENDER'):
        os.environ['ENVIRONMENT'] = 'production'
        print("🌐 RENDER PRODUCTION mode")
        port = int(os.environ.get('PORT', 10000))  # Render provides PORT
    else:
        existing_env = os.environ.get('ENVIRONMENT', 'development')
        os.environ['ENVIRONMENT'] = existing_env
        print(f"📍 {existing_env.upper()} mode")
        port = 5001 if existing_env == "development" else 5000

# Create the app
app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # Show which database we're using (but hide sensitive info in production)
        from config import Config
        db_info = Config.get_db_info()
        
        if Config.IS_DEVELOPMENT:
            print(f"🗄️  Database: {db_info['current_env']} -> {db_info['database_uri'].split('/')[-1]}")
        else:
            # In production, just show that we're connected without exposing credentials
            db_name = db_info['database_uri'].split('/')[-1] if '/' in db_info['database_uri'] else 'connected'
            print(f"🗄️  Database: {db_info['current_env']} -> {db_name}")
        
        # Create tables
        try:
            db.create_all()
            print("✅ Database tables created/verified")
        except Exception as e:
            print(f"❌ Database error: {e}")
            
        print(f"🚀 Ready on port {port}")

    # Run the app
    if Config.IS_DEVELOPMENT:
        app.run(debug=True, port=port, use_reloader=False)
    else:
        # In production, Gunicorn will handle this
        app.run(host='0.0.0.0', port=port, debug=False)