# 1. First, add these to your requirements.txt:
# Flask-HTTPAuth==4.8.0

# 2. Create a new file: app/auth.py
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash
import os

auth = HTTPBasicAuth()

# In production, this should come from environment variables
# For now, you can set a simple shared password
SHARED_PASSWORD = os.getenv('SHARED_PASSWORD', '403')  # Change this!

# Generate the hash once (you can run this in Python to get the hash)
# from werkzeug.security import generate_password_hash
# print(generate_password_hash('roommates2024!'))
PASSWORD_HASH = generate_password_hash(SHARED_PASSWORD)

@auth.verify_password
def verify_password(username, password):
    # For simplicity, any username works, just need correct password
    if username == 'roommate' and check_password_hash(PASSWORD_HASH, password):
        return username
    return None

@auth.error_handler
def auth_error():
    return '''
    <html>
    <head><title>Access Required</title></head>
    <body style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h2>🏠 Roommate Expense Tracker</h2>
        <p>Please enter the shared password to access the app.</p>
        <p><em>Username: roommate</em></p>
    </body>
    </html>
    ''', 401