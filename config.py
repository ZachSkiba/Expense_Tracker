import os
from dotenv import load_dotenv
import sys

def detect_environment():
    """Detect environment with proper priority order"""
    # Check for Render environment first
    if os.environ.get('RENDER'):
        return 'production'
        
    # Check command line arguments
    if '--dev' in sys.argv or '--development' in sys.argv:
        return 'development'
    elif '--prod' in sys.argv or '--production' in sys.argv:
        return 'production'
    
    # Check ENVIRONMENT variable
    env_var = os.environ.get('ENVIRONMENT')
    if env_var in ['development', 'production']:
        return env_var
    
    # Default to development
    return 'development'

def load_environment_config():
    """Load the correct environment file and return config info"""
    current_env = detect_environment()
    is_development = (current_env == 'development')
    
    # Only load .env files in development (Render uses environment variables)
    if is_development:
        env_file = '.env.dev'
        if os.path.exists(env_file):
            load_dotenv(dotenv_path=env_file)
    else:
        env_file = 'render-environment-variables'
    
    return current_env, is_development, env_file

# Load environment
_current_env, _is_development, _env_file = load_environment_config()

class Config:
    # Environment info
    CURRENT_ENV = _current_env
    IS_DEVELOPMENT = _is_development
    ENV_FILE = _env_file
    
    # Database configuration
    if IS_DEVELOPMENT:
        # Development: Use local database with psycopg2
        SQLALCHEMY_DATABASE_URI = os.getenv(
            'DATABASE_URL', 
            'postgresql://postgres:1234@localhost/expense_tracker_dev'
        )
        if SQLALCHEMY_DATABASE_URI.startswith('postgresql://') and '+psycopg' not in SQLALCHEMY_DATABASE_URI:
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgresql://', 'postgresql+psycopg://', 1)

    else:
    # Production: Use Neon database with psycopg3
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            # Fix postgres:// to postgresql:// if needed (common issue)
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            # For psycopg3, we need to ensure the URL uses the right driver
            if 'postgresql://' in database_url and '+psycopg' not in database_url:
                database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
            
            # 🔑 Force SSL if not already set
            if "sslmode" not in database_url:
                if "?" in database_url:
                    database_url += "&sslmode=require"
                else:
                    database_url += "?sslmode=require"
            
            SQLALCHEMY_DATABASE_URI = database_url
        else:
            # Fallback (shouldn't happen on Render)
            SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://postgres:1234@localhost/expense_tracker'

        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {
                'connect_timeout': 10,
                'sslmode': 'prefer'  # Less strict SSL
            }
        }
    
    # Other configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Force DEBUG off in production
    if not IS_DEVELOPMENT:
        DEBUG = False
    
    @classmethod
    def get_db_info(cls):
        return {
            'database_uri': cls.SQLALCHEMY_DATABASE_URI,
            'is_development': cls.IS_DEVELOPMENT,
            'env_file': cls.ENV_FILE,
            'debug': cls.DEBUG,
            'current_env': cls.CURRENT_ENV
        }