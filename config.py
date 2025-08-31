import os
from dotenv import load_dotenv
import sys

def detect_environment():
    """Detect environment with proper priority order"""
    print(f"[DEBUG] sys.argv: {sys.argv}")
    
    # 1. Check command line arguments first (highest priority)
    if '--dev' in sys.argv or '--development' in sys.argv:
        print("[DEBUG] Found --dev or --development in sys.argv")
        return 'development'
    elif '--prod' in sys.argv or '--production' in sys.argv:
        print("[DEBUG] Found --prod or --production in sys.argv")
        return 'production'
    
    # 2. Check ENVIRONMENT variable (set by run.py)
    env_var = os.environ.get('ENVIRONMENT')
    print(f"[DEBUG] ENVIRONMENT variable: {env_var}")
    if env_var in ['development', 'production']:
        return env_var
    
    # 3. Default to development
    print("[DEBUG] Defaulting to development")
    return 'development'

def load_environment_config():
    """Load the correct environment file and return config info"""
    current_env = detect_environment()
    is_development = (current_env == 'development')
    
    # Use .env.dev for development, .env for production
    env_file = '.env.dev' if is_development else '.env'
    
    print(f"[DEBUG] Current env: {current_env}")
    print(f"[DEBUG] Is development: {is_development}")
    print(f"[DEBUG] Loading env file: {env_file}")
    print(f"[DEBUG] Env file exists: {os.path.exists(env_file)}")
    
    # Load the environment file
    result = load_dotenv(dotenv_path=env_file)
    print(f"[DEBUG] load_dotenv result: {result}")
    
    # Check what DATABASE_URL is after loading
    database_url_after_load = os.getenv('DATABASE_URL')
    print(f"[DEBUG] DATABASE_URL after load_dotenv: {database_url_after_load}")
    
    return current_env, is_development, env_file

# Load environment immediately when module is imported
print("[DEBUG] Starting config.py import...")
_current_env, _is_development, _env_file = load_environment_config()

class Config:
    # Environment info
    CURRENT_ENV = _current_env
    IS_DEVELOPMENT = _is_development
    ENV_FILE = _env_file
    
    print(f"[DEBUG] Setting up Config class...")
    print(f"[DEBUG] IS_DEVELOPMENT = {IS_DEVELOPMENT}")
    
    # Database configuration based on environment
    if IS_DEVELOPMENT:
        default_db = 'postgresql://postgres:1234@localhost/expense_tracker_dev'
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', default_db)
        print(f"🔧 DEV: Using database -> {SQLALCHEMY_DATABASE_URI}")
    else:
        default_db = 'postgresql://postgres:1234@localhost/expense_tracker'
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', default_db)
        print(f"🚀 PROD: Using database -> {SQLALCHEMY_DATABASE_URI}")
    
    # Other Flask config
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"[DEBUG] Final SQLALCHEMY_DATABASE_URI: {SQLALCHEMY_DATABASE_URI}")
    print(f"[DEBUG] Config setup complete")
    
    @classmethod
    def get_db_info(cls):
        return {
            'database_uri': cls.SQLALCHEMY_DATABASE_URI,
            'is_development': cls.IS_DEVELOPMENT,
            'env_file': cls.ENV_FILE,
            'debug': cls.DEBUG,
            'current_env': cls.CURRENT_ENV
        }