# app/routes/admin.py - Final version

import datetime
from flask import Blueprint, render_template, jsonify, redirect, url_for, request
from flask import current_app
from models import db, RecurringPayment
from datetime import date

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/recurring')
def recurring_admin_dashboard():
    """Serve the recurring payments admin dashboard"""
    if not current_app.config.get('ADMIN_ACCESS_ENABLED', False):
        return jsonify({'error': 'Admin access disabled'}), 403
    
    try:
        from app.auth import check_auth
        if not check_auth():
            return redirect(url_for('login'))
    except ImportError:
        if not current_app.debug:
            return jsonify({'error': 'Authentication required'}), 403
    
    return render_template('admin_dashboard.html')

@admin.route('/health')
def health_check():
    """Health check for the admin system"""
    try:
        today = date.today()
        
        # Get payment statistics
        total_active = RecurringPayment.query.filter(RecurringPayment.is_active == True).count()
        due_today = RecurringPayment.query.filter(
            RecurringPayment.is_active == True,
            RecurringPayment.next_due_date <= today
        ).count()
        
        return jsonify({
            'status': 'healthy',
            'payments': {
                'total_active': total_active,
                'due_today': due_today
            },
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@admin.route('/recurring/status')
def get_recurring_status():
    """Get comprehensive recurring payments status"""
    try:
        from app.auth import check_auth
        if not check_auth():
            return jsonify({'error': 'Authentication required'}), 403
    except ImportError:
        if not current_app.debug:
            return jsonify({'error': 'Authentication required'}), 403
    
    try:
        from datetime import timedelta
        today = date.today()
        
        # Get payment statistics
        total_active = RecurringPayment.query.filter(RecurringPayment.is_active == True).count()
        
        due_today = RecurringPayment.query.filter(
            RecurringPayment.is_active == True,
            RecurringPayment.next_due_date <= today
        ).all()
        
        due_tomorrow = RecurringPayment.query.filter(
            RecurringPayment.is_active == True,
            RecurringPayment.next_due_date == today + timedelta(days=1)
        ).all()
        
        overdue = RecurringPayment.query.filter(
            RecurringPayment.is_active == True,
            RecurringPayment.next_due_date < today
        ).all()
        
        return jsonify({
            'success': True,
            'system': {
                'type': 'startup_processor',
                'description': 'Processes missed payments on app startup'
            },
            'payments': {
                'total_active': total_active,
                'due_today': len(due_today),
                'due_tomorrow': len(due_tomorrow),
                'overdue': len(overdue)
            },
            'details': {
                'due_today': [{
                    'id': p.id, 
                    'category': p.category_obj.name, 
                    'amount': p.amount, 
                    'user': p.user.name,
                    'next_due_date': p.next_due_date.isoformat()
                } for p in due_today],
                'overdue': [{
                    'id': p.id, 
                    'category': p.category_obj.name, 
                    'amount': p.amount, 
                    'due_date': p.next_due_date.isoformat(), 
                    'user': p.user.name,
                    'days_overdue': (today - p.next_due_date).days
                } for p in overdue]
            },
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin.route('/recurring/process-all', methods=['POST'])
def manual_process_all():
    """Manually process all due recurring payments"""
    try:
        from app.auth import check_auth
        if not check_auth():
            return jsonify({'error': 'Authentication required'}), 403
    except ImportError:
        if not current_app.debug:
            return jsonify({'error': 'Authentication required'}), 403
    
    try:
        from app.services.recurring_service import RecurringPaymentService
        
        print("Manual processing of all due payments triggered")
        created_expenses = RecurringPaymentService.process_due_payments()
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(created_expenses)} due recurring payments',
            'expenses_created': len(created_expenses),
            'details': [
                {
                    'expense_id': expense.id,
                    'amount': expense.amount,
                    'category': expense.category_obj.name,
                    'user': expense.user.name,
                    'date': expense.date.isoformat()
                } for expense in created_expenses
            ]
        })
        
    except Exception as e:
        print(f"Manual processing failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin.route('/recurring/wake-and-process', methods=['POST'])
def wake_and_process():
    """Special endpoint for external triggers to wake app and process payments"""
    
    # Log the incoming request for debugging
    print(f"[WAKE_AND_PROCESS] Request received from {request.remote_addr}")
    print(f"[WAKE_AND_PROCESS] User-Agent: {request.headers.get('User-Agent', 'None')}")
    print(f"[WAKE_AND_PROCESS] Path: {request.path}")
    print(f"[WAKE_AND_PROCESS] Endpoint: {request.endpoint}")
    
    # Simple security check - validate request source
    import os
    
    # Check for automation secret (optional but recommended)
    automation_secret = os.getenv('AUTOMATION_SECRET')
    if automation_secret:
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {automation_secret}':
            print("[WAKE_AND_PROCESS] Unauthorized: Missing or invalid authorization header")
            return jsonify({'error': 'Unauthorized'}), 401
    
    # Additional validation: Check User-Agent for GitHub Actions
    user_agent = request.headers.get('User-Agent', '')
    if not any(source in user_agent for source in ['GitHub-Actions', 'curl']):
        print(f"[WAKE_AND_PROCESS] Suspicious user agent: {user_agent}")
        return jsonify({'error': 'Invalid request source'}), 403
    
    try:
        from app.services.recurring_service import RecurringPaymentService
        from app.startup_processor import StartupRecurringProcessor
        
        # Log the trigger source
        request_data = request.get_json() or {}
        source = request_data.get('source', 'unknown')
        print(f"[WAKE_AND_PROCESS] Triggered by: {source}")
        
        # Run both startup processor (catch missed) and regular processor (handle due)
        print("[WAKE_AND_PROCESS] Running startup processor to catch missed payments...")
        StartupRecurringProcessor.process_startup_recurring_payments(current_app)
        
        print("[WAKE_AND_PROCESS] Running due payments processor...")
        created_expenses = RecurringPaymentService.process_due_payments()
        
        result = {
            'success': True,
            'message': f'Wake-and-process completed. Created {len(created_expenses)} expenses.',
            'expenses_created': len(created_expenses),
            'source': source,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        print(f"[WAKE_AND_PROCESS] Completed successfully: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"[WAKE_AND_PROCESS] Failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500