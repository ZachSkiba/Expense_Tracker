# app/templates/group_templates.py

def get_groups_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>My Groups - Expense Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #1a202c;
        }
        .header {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .nav-links a {
            margin-left: 1rem;
            color: #4a5568;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .nav-links a:hover { background: #edf2f7; }
        .main { padding: 2rem; max-width: 800px; margin: 0 auto; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 1.5rem;
        }
        .btn {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #4299e1;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.875rem;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
            margin-right: 1rem;
        }
        .btn:hover { background: #3182ce; }
        .btn-secondary { background: #718096; }
        .btn-secondary:hover { background: #4a5568; }
        .group-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .group-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }
        .group-title { color: #2d3748; margin-bottom: 0.5rem; }
        .group-meta { color: #718096; font-size: 0.875rem; }
        .group-actions a { font-size: 0.75rem; padding: 0.5rem 1rem; }
        .flash-success {
            background: #f0fff4;
            color: #22543d;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            border: 1px solid #9ae6b4;
            margin-bottom: 0.5rem;
        }
        .flash-error {
            background: #fed7d7;
            color: #742a2a;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            border: 1px solid #feb2b2;
            margin-bottom: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>💰 Expense Tracker</h1>
        <div class="nav-links">
            <a href="{{ url_for('dashboard.home') }}">Dashboard</a>
            <a href="{{ url_for('groups.index') }}">Groups</a>
            <a href="{{ url_for('auth.profile') }}">Profile</a>
            <a href="{{ url_for('auth.logout') }}">Logout</a>
        </div>
    </div>

    <div class="main">
        <div class="flash-messages">
            {% for category, message in get_flashed_messages(with_categories=true) %}
                <div class="flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        </div>

        <h1>My Groups</h1>
        
        <div style="margin: 2rem 0;">
            <a href="{{ url_for('groups.create') }}" class="btn">Create New Group</a>
            <a href="{{ url_for('groups.join') }}" class="btn btn-secondary">Join Existing Group</a>
        </div>

        {% if user_groups %}
            {% for group in user_groups %}
            <div class="group-card">
                <div class="group-header">
                    <div>
                        <h3 class="group-title">{{ group.name }}</h3>
                        <div class="group-meta">
                            {{ group.get_member_count() }} members • 
                            Created {{ group.created_at.strftime('%b %d, %Y') }}
                            {% if group.creator_id == current_user.id %}• You are the admin{% endif %}
                        </div>
                        {% if group.description %}
                        <p style="margin-top: 0.5rem; color: #4a5568;">{{ group.description }}</p>
                        {% endif %}
                    </div>
                    <div class="group-actions">
                        <a href="{{ url_for('groups.detail', group_id=group.id) }}" class="btn">View Details</a>
                    </div>
                </div>
                
                <div style="background: #f7fafc; padding: 1rem; border-radius: 6px; margin-top: 1rem;">
                    <strong>Invite Code:</strong> {{ group.invite_code }}
                    <small style="color: #718096; margin-left: 1rem;">Share this code with friends to invite them</small>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="card" style="text-align: center; padding: 3rem;">
                <h3 style="color: #718096; margin-bottom: 1rem;">No Groups Yet</h3>
                <p style="color: #a0aec0; margin-bottom: 2rem;">Create your first group or join an existing one to start tracking shared expenses</p>
                <a href="{{ url_for('groups.create') }}" class="btn">Create Your First Group</a>
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

def get_create_group_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Create Group - Expense Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* Reuse auth styles */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .form-container {
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 500px;
        }
        .form-header { text-align: center; margin-bottom: 2rem; }
        .form-title { font-size: 1.875rem; font-weight: bold; color: #1f2937; margin-bottom: 0.5rem; }
        .form-subtitle { color: #6b7280; font-size: 0.875rem; }
        .form-group { margin-bottom: 1.5rem; }
        .form-label { display: block; font-weight: 500; color: #374151; margin-bottom: 0.5rem; }
        .form-input, .form-textarea {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: all 0.2s;
            background: #f9fafb;
        }
        .form-textarea { min-height: 100px; resize: vertical; }
        .form-input:focus, .form-textarea:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.875rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        .back-link {
            text-align: center;
            margin-top: 1.5rem;
        }
        .back-link a {
            color: #667eea;
            text-decoration: none;
            font-size: 0.875rem;
        }
        .flash-error {
            background: #fef2f2;
            color: #dc2626;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #fecaca;
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <div class="form-header">
            <h1 class="form-title">Create New Group</h1>
            <p class="form-subtitle">Start tracking shared expenses with friends</p>
        </div>
        
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="flash-{{ category }}">{{ message }}</div>
        {% endfor %}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label" for="name">Group Name *</label>
                <input type="text" 
                       id="name" 
                       name="name" 
                       class="form-input" 
                       placeholder="e.g., Roommates, Trip to Paris"
                       value="{{ request.form.get('name', '') }}"
                       required>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="description">Description (Optional)</label>
                <textarea id="description" 
                         name="description" 
                         class="form-textarea" 
                         placeholder="What is this group for?">{{ request.form.get('description', '') }}</textarea>
            </div>
            
            <button type="submit" class="btn">Create Group</button>
        </form>
        
        <div class="back-link">
            <a href="{{ url_for('groups.index') }}">&larr; Back to Groups</a>
        </div>
    </div>
</body>
</html>
'''

def get_join_group_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Join Group - Expense Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* Reuse create group styles */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }
        .form-container {
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
        .form-header { text-align: center; margin-bottom: 2rem; }
        .form-title { font-size: 1.875rem; font-weight: bold; color: #1f2937; margin-bottom: 0.5rem; }
        .form-subtitle { color: #6b7280; font-size: 0.875rem; }
        .form-group { margin-bottom: 1.5rem; }
        .form-label { display: block; font-weight: 500; color: #374151; margin-bottom: 0.5rem; }
        .form-input {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: all 0.2s;
            background: #f9fafb;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-align: center;
        }
        .form-input:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.875rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        .back-link {
            text-align: center;
            margin-top: 1.5rem;
        }
        .back-link a {
            color: #667eea;
            text-decoration: none;
            font-size: 0.875rem;
        }
        .flash-error {
            background: #fef2f2;
            color: #dc2626;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #fecaca;
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
        }
        .flash-info {
            background: #eff6ff;
            color: #1e40af;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #bfdbfe;
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
        }
        .help-text {
            font-size: 0.75rem;
            color: #6b7280;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <div class="form-header">
            <h1 class="form-title">Join Group</h1>
            <p class="form-subtitle">Enter the invite code from your friend</p>
        </div>
        
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="flash-{{ category }}">{{ message }}</div>
        {% endfor %}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label" for="invite_code">Invite Code</label>
                <input type="text" 
                       id="invite_code" 
                       name="invite_code" 
                       class="form-input" 
                       placeholder="Enter 8-character code"
                       value="{{ request.form.get('invite_code', '') }}"
                       maxlength="8"
                       required>
                <div class="help-text">
                    Ask a group member for the invite code
                </div>
            </div>
            
            <button type="submit" class="btn">Join Group</button>
        </form>
        
        <div class="back-link">
            <a href="{{ url_for('groups.index') }}">&larr; Back to Groups</a>
        </div>
    </div>
</body>
</html>
'''

def get_group_detail_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ group.name }} - Expense Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* Reuse dashboard styles */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #1a202c;
        }
        .header {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .nav-links a {
            margin-left: 1rem;
            color: #4a5568;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .nav-links a:hover { background: #edf2f7; }
        .main { padding: 2rem; max-width: 1000px; margin: 0 auto; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 1.5rem;
        }
        .group-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2rem;
        }
        .group-info h1 { color: #2d3748; margin-bottom: 0.5rem; }
        .group-meta { color: #718096; margin-bottom: 1rem; }
        .invite-code {
            background: #f7fafc;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            margin: 1rem 0;
        }
        .btn {
            display: inline-block;
            padding: 0.5rem 1rem;
            background: #4299e1;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.875rem;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
            margin-right: 0.5rem;
        }
        .btn:hover { background: #3182ce; }
        .btn-danger { background: #e53e3e; }
        .btn-danger:hover { background: #c53030; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            text-align: center;
            padding: 1.5rem;
            background: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2b6cb0;
            margin-bottom: 0.5rem;
        }
        .stat-label { color: #718096; font-size: 0.875rem; }
        .expense-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .expense-item:last-child { border-bottom: none; }
        .expense-info h4 { color: #2d3748; font-size: 0.875rem; margin-bottom: 0.25rem; }
        .expense-info p { color: #718096; font-size: 0.75rem; }
        .expense-amount { font-weight: bold; color: #e53e3e; }
        .balance-positive { color: #38a169; }
        .balance-negative { color: #e53e3e; }
        .flash-success {
            background: #f0fff4;
            color: #22543d;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            border: 1px solid #9ae6b4;
            margin-bottom: 0.5rem;
        }
        .flash-error {
            background: #fed7d7;
            color: #742a2a;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            border: 1px solid #feb2b2;
            margin-bottom: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>💰 Expense Tracker</h1>
        <div class="nav-links">
            <a href="{{ url_for('dashboard.home') }}">Dashboard</a>
            <a href="{{ url_for('groups.index') }}">Groups</a>
            <a href="{{ url_for('auth.profile') }}">Profile</a>
            <a href="{{ url_for('auth.logout') }}">Logout</a>
        </div>
    </div>

    <div class="main">
        <div class="flash-messages">
            {% for category, message in get_flashed_messages(with_categories=true) %}
                <div class="flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        </div>

        <div class="group-header">
            <div class="group-info">
                <h1>{{ group.name }}</h1>
                <div class="group-meta">
                    {{ group.get_member_count() }} members • 
                    Created {{ group.created_at.strftime('%b %d, %Y') }}
                    {% if is_admin %}• You are an admin{% endif %}
                </div>
                {% if group.description %}
                <p>{{ group.description }}</p>
                {% endif %}
                
                <div class="invite-code">
                    <strong>Invite Code:</strong> {{ group.invite_code }}
                    <small style="color: #718096; margin-left: 1rem;">Share this with friends to invite them</small>
                </div>
            </div>
            <div>
                <a href="#" class="btn">Add Expense</a>
                {% if is_admin %}
                <a href="#" class="btn">Manage Group</a>
                {% else %}
                <form method="post" action="{{ url_for('groups.leave', group_id=group.id) }}" style="display: inline;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Are you sure you want to leave this group?')">Leave Group</button>
                </form>
                {% endif %}
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">${{ "%.2f"|format(monthly_total) }}</div>
                <div class="stat-label">Spent This Month</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {% if user_balance > 0 %}balance-positive{% elif user_balance < 0 %}balance-negative{% endif %}">
                    {% if user_balance > 0 %}+{% elif user_balance < 0 %}-{% endif %}${{ "%.2f"|format(abs(user_balance)) }}
                </div>
                <div class="stat-label">Your Balance</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ recent_expenses|length }}</div>
                <div class="stat-label">Recent Expenses</div>
            </div>
        </div>

        {% if recent_expenses %}
        <div class="card">
            <h3>Recent Expenses</h3>
            {% for expense in recent_expenses %}
            <div class="expense-item">
                <div class="expense-info">
                    <h4>{{ expense.category_obj.name }}</h4>
                    <p>{{ expense.user.name }} • {{ expense.date.strftime('%b %d, %Y') }}</p>
                    {% if expense.category_description %}
                    <p>{{ expense.category_description }}</p>
                    {% endif %}
                </div>
                <div class="expense-amount">${{ "%.2f"|format(expense.amount) }}</div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="card" style="text-align: center; padding: 2rem;">
            <h3 style="color: #718096; margin-bottom: 1rem;">No Expenses Yet</h3>
            <p style="color: #a0aec0; margin-bottom: 2rem;">Start tracking your group expenses</p>
            <a href="#" class="btn">Add First Expense</a>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''