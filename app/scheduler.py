# app/scheduler.py - Complete production scheduler system

from flask_apscheduler import APScheduler
from datetime import datetime, date, timedelta
import logging
import os
from functools import wraps

# Set up logging specifically for scheduler
scheduler_logger = logging.getLogger('recurring_scheduler')
scheduler_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# File handler for scheduler logs
file_handler = logging.FileHandler(os.path.join(logs_dir, 'recurring_scheduler.log'))
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

scheduler_logger.addHandler(file_handler)
scheduler_logger.addHandler(console_handler)

class RecurringPaymentScheduler:
    def __init__(self, app=None):
        self.app = app
        self.scheduler = APScheduler()
        self.last_run_status = {
            'last_run': None,
            'status': 'never_run',
            'expenses_created': 0,
            'error': None,
            'execution_time': 0
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the scheduler with the Flask app"""
        self.app = app
        
        # Configure scheduler settings
        app.config.setdefault('SCHEDULER_API_ENABLED', True)
        app.config.setdefault('SCHEDULER_TIMEZONE', 'America/New_York')  # Adjust to your timezone
        app.config.setdefault('RECURRING_SCHEDULE_HOUR', 6)  # 6 AM
        app.config.setdefault('RECURRING_SCHEDULE_MINUTE', 0)
        
        # Initialize scheduler with app
        self.scheduler.init_app(app)
        
        # Add the recurring payment job
        self.add_recurring_job()
        
        # Add monitoring/admin routes
        self.add_admin_routes()
        
        # Start scheduler if enabled
        if app.config.get('SCHEDULER_ENABLED', False):
            try:
                self.scheduler.start()
                scheduler_logger.info("Recurring payments scheduler started successfully")
            except Exception as e:
                scheduler_logger.error(f"Failed to start scheduler: {e}")
    
    def add_recurring_job(self):
        """Add the main recurring payment processing job"""
        
        @self.scheduler.task(
            'cron',
            id='process_recurring_payments',
            hour=self.app.config.get('RECURRING_SCHEDULE_HOUR', 6),
            minute=self.app.config.get('RECURRING_SCHEDULE_MINUTE', 0),
            misfire_grace_time=300  # Allow 5 minutes grace period
        )
        def scheduled_recurring_payments():
            """Main scheduled task to process recurring payments"""
            with self.app.app_context():
                self.process_recurring_payments()
    
    def process_recurring_payments(self):
        """Process due recurring payments with comprehensive logging"""
        start_time = datetime.now()
        scheduler_logger.info("=== Starting scheduled recurring payments processing ===")
        
        try:
            from app.services.recurring_service import RecurringPaymentService
            from models import RecurringPayment
            
            # Get statistics before processing
            total_active = RecurringPayment.query.filter(RecurringPayment.is_active == True).count()
            due_today = RecurringPayment.query.filter(
                RecurringPayment.is_active == True,
                RecurringPayment.next_due_date <= date.today()
            ).count()
            
            scheduler_logger.info(f"Total active recurring payments: {total_active}")
            scheduler_logger.info(f"Payments due for processing: {due_today}")
            
            # Process due payments
            created_expenses = RecurringPaymentService.process_due_payments()
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update status
            self.last_run_status = {
                'last_run': start_time.isoformat(),
                'status': 'success',
                'expenses_created': len(created_expenses),
                'error': None,
                'execution_time': execution_time,
                'total_active': total_active,
                'due_today': due_today
            }
            
            if created_expenses:
                scheduler_logger.info(f"✅ Successfully processed {len(created_expenses)} recurring payments:")
                for expense in created_expenses:
                    scheduler_logger.info(f"   - Created expense ID {expense.id}: {expense.category_obj.name} - ${expense.amount:.2f} (paid by {expense.user.name})")
                
                # Send notifications if configured
                self.send_notifications(created_expenses)
                
            else:
                scheduler_logger.info("✅ No recurring payments were due for processing")
            
            scheduler_logger.info(f"=== Completed successfully in {execution_time:.2f} seconds ===")
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update status with error
            self.last_run_status = {
                'last_run': start_time.isoformat(),
                'status': 'error',
                'expenses_created': 0,
                'error': str(e),
                'execution_time': execution_time
            }
            
            scheduler_logger.error(f"❌ Error processing recurring payments: {e}")
            scheduler_logger.exception("Full traceback:")
            
            # Send error notification if configured
            self.send_error_notification(e)
    
    def send_notifications(self, created_expenses):
        """Send success notifications (implement as needed)"""
        try:
            # Example: Log for now, but you could integrate with:
            # - Email service (SendGrid, SMTP)
            # - Slack webhook
            # - Discord webhook
            # - SMS service
            
            notification_config = self.app.config.get('RECURRING_NOTIFICATIONS', {})
            
            if notification_config.get('enabled', False):
                scheduler_logger.info(f"📧 Would send success notification about {len(created_expenses)} processed payments")
                # TODO: Implement actual notification sending
                
        except Exception as e:
            scheduler_logger.warning(f"Failed to send success notification: {e}")
    
    def send_error_notification(self, error):
        """Send error notifications (implement as needed)"""
        try:
            notification_config = self.app.config.get('RECURRING_NOTIFICATIONS', {})
            
            if notification_config.get('enabled', False) and notification_config.get('send_errors', True):
                scheduler_logger.info(f"🚨 Would send error notification about: {error}")
                # TODO: Implement actual error notification sending
                
        except Exception as e:
            scheduler_logger.warning(f"Failed to send error notification: {e}")
    
    def add_admin_routes(self):
        """Add administrative routes for monitoring and control"""
        
        def admin_required(f):
            """Simple admin check (implement proper auth as needed)"""
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # TODO: Add proper authentication check
                # For now, just check if in debug mode or has admin key
                if not self.app.debug and not self.app.config.get('ADMIN_ACCESS_ENABLED', False):
                    from flask import jsonify
                    return jsonify({'error': 'Admin access required'}), 403
                return f(*args, **kwargs)
            return decorated_function
        
        @self.app.route('/admin/recurring/status', methods=['GET'])
        @admin_required
        def get_scheduler_status():
            """Get comprehensive scheduler status"""
            from flask import jsonify
            from models import RecurringPayment
            
            try:
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
                
                # Scheduler status
                scheduler_running = self.scheduler.running if hasattr(self.scheduler, 'running') else False
                
                return jsonify({
                    'success': True,
                    'scheduler': {
                        'running': scheduler_running,
                        'timezone': self.app.config.get('SCHEDULER_TIMEZONE'),
                        'schedule': f"{self.app.config.get('RECURRING_SCHEDULE_HOUR', 6)}:{self.app.config.get('RECURRING_SCHEDULE_MINUTE', 0):02d}",
                        'last_run': self.last_run_status
                    },
                    'payments': {
                        'total_active': total_active,
                        'due_today': len(due_today),
                        'due_tomorrow': len(due_tomorrow),
                        'overdue': len(overdue)
                    },
                    'details': {
                        'due_today': [{'id': p.id, 'category': p.category_obj.name, 'amount': p.amount, 'user': p.user.name} for p in due_today],
                        'overdue': [{'id': p.id, 'category': p.category_obj.name, 'amount': p.amount, 'due_date': p.next_due_date.isoformat(), 'user': p.user.name} for p in overdue]
                    },
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/admin/recurring/run-now', methods=['POST'])
        @admin_required
        def manual_run_recurring():
            """Manually trigger recurring payment processing"""
            from flask import jsonify
            
            try:
                scheduler_logger.info("Manual recurring payment processing triggered")
                self.process_recurring_payments()
                
                return jsonify({
                    'success': True,
                    'message': 'Recurring payment processing completed',
                    'result': self.last_run_status
                })
                
            except Exception as e:
                scheduler_logger.error(f"Manual processing failed: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/admin/recurring/logs', methods=['GET'])
        @admin_required
        def get_scheduler_logs():
            """Get recent scheduler logs"""
            from flask import jsonify, request
            
            try:
                lines = int(request.args.get('lines', 50))
                log_file = os.path.join(logs_dir, 'recurring_scheduler.log')
                
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        log_lines = f.readlines()
                    
                    # Get last N lines
                    recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
                    
                    return jsonify({
                        'success': True,
                        'logs': [line.strip() for line in recent_logs],
                        'total_lines': len(log_lines)
                    })
                else:
                    return jsonify({
                        'success': True,
                        'logs': [],
                        'message': 'No log file found'
                    })
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

# Global instance
recurring_scheduler = RecurringPaymentScheduler()