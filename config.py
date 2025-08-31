import os
from dotenv import load_dotenv

# Load .env.dev if FLASK_ENV=development, otherwise load default .env
env_file = '.env'
if os.environ.get('FLASK_ENV') == 'development':
    env_file = '.env.dev'

load_dotenv(dotenv_path=env_file)

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'postgresql://postgres:1234@localhost/expense_tracker'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')  # <-- don’t forget this!
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
