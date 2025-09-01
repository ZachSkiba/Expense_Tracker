# Simple session-based authentication for roommates
from flask import session, request, redirect, url_for, render_template_string
import os

# Simple shared password
SHARED_PASSWORD = os.getenv('SHARED_PASSWORD', '403')

def check_auth():
    """Check if user is authenticated"""
    return session.get('authenticated') == True

def authenticate(password):
    """Authenticate with shared password"""
    if password == SHARED_PASSWORD:
        session['authenticated'] = True
        return True
    return False

def require_auth():
    """Decorator/function to require authentication"""
    if request.endpoint == 'static':
        return None
        
    if request.endpoint == 'login':
        return None
        
    if not check_auth():
        return redirect(url_for('login'))
    
    return None

# Login page template
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Roommate Expense Tracker - Login</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }
        .login-box {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            min-width: 300px;
        }
        .error { color: red; margin-bottom: 1rem; }
        input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            margin: 1rem 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
        }
        button {
            background: #667eea;
            color: white;
            padding: 0.75rem 2rem;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            cursor: pointer;
        }
        button:hover { background: #5a6fd8; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🏠 Roommate Expense Tracker</h2>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form method="post">
            <div>
                <input type="password" name="password" placeholder="Enter shared password" required autofocus>
            </div>
            <button type="submit">Access App</button>
        </form>
        <p style="margin-top: 1rem; color: #666; font-size: 0.9rem;">
            Ask your roommates for the shared password
        </p>
    </div>
</body>
</html>
'''