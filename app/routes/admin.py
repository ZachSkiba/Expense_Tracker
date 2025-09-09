# app/routes/admin.py

import datetime
from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask import current_app

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/recurring')
def recurring_admin_dashboard():
    """Serve the recurring payments admin dashboard"""
    # Check if admin access is enabled and user is authenticated
    if not current_app.config.get('ADMIN_ACCESS_ENABLED', False):
        return jsonify({'error': 'Admin access disabled'}), 403
    
    # Check authentication using your existing auth system
    try:
        from app.auth import check_auth
        if not check_auth():
            return redirect(url_for('login'))
    except ImportError:
        # Fallback if auth module not found
        if not current_app.debug:
            return jsonify({'error': 'Authentication required'}), 403
    
    return render_template('admin_dashboard.html')

@admin.route('/health')
def health_check():
    """Simple health check for the admin system"""
    try:
        from app.scheduler import recurring_scheduler
        
        scheduler_status = {
            'running': getattr(recurring_scheduler.scheduler, 'running', False),
            'last_run': recurring_scheduler.last_run_status
        }
        
        return jsonify({
            'status': 'healthy',
            'scheduler': scheduler_status,
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500