import os
from dotenv import load_dotenv
import sys

class Config:
    @staticmethod
    def detect_environment():
        """Detect environment with proper priority order"""
        # 1. Check command line arguments first (highest priority)
        if '--dev' in sys.argv or '--development' in sys.argv:
            return 'development'
        elif '--prod' in sys.argv or '--production' in sys.argv:
            return 'production'
        
        # 2. Check ENVIRONMENT variable (set by run.py)
        env_var = os.environ.get('ENVIRONMENT')
        if env_var in ['development', 'production']:
            return env_var
        
        # 3. Default to development
        return 'development'
    
    @staticmethod
    def load_environment():
        """Load the correct environment file and return config info"""
        current_env = Config.detect_environment()
        is_development = (current_env == 'development')
        
        # Use .env.dev for development, .env for production
        env_file = '.env.dev' if is_development else '.env'
        
        # Load the environment file
        load_dotenv(dotenv_path=env_file)
        
        return current_env, is_development, env_file

# Load environment immediately when module is imported
_current_env, _is_development, _env_file = Config.load_environment()

class Config:
    # Database configuration based on environment
    if _is_development:
        SQLALCHEMY_DATABASE_URI = os.getenv(
            'DATABASE_URL', 
            'postgresql://postgres:1234@localhost/expense_tracker_dev'
        )
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv(
            'DATABASE_URL', 
            'postgresql://postgres:1234@localhost/expense_tracker'
        )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Store environment info as class attributes
    CURRENT_ENV = _current_env
    IS_DEVELOPMENT = _is_development
    ENV_FILE = _env_file
    
    @classmethod
    def get_db_info(cls):
        return {
            'database_uri': cls.SQLALCHEMY_DATABASE_URI,
            'is_development': cls.IS_DEVELOPMENT,
            'env_file': cls.ENV_FILE,
            'debug': cls.DEBUG,
            'current_env': cls.CURRENT_ENV
        }