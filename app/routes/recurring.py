# Fixed recurring.py routes with proper group context and balance updates

from flask import Blueprint, request, jsonify
from models import db, RecurringPayment, User, Category, Group
from app.services.recurring_service import RecurringPaymentService
from balance_service import BalanceService
from datetime import datetime, date
from flask_login import current_user
import logging

# Set up logging
logger = logging.getLogger(__name__)

recurring = Blueprint('recurring', __name__, url_prefix='/api/recurring')

@recurring.route('/payments/<int:group_id>', methods=['GET'])
def get_recurring_payments_api(group_id):
    """Get all recurring payments for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get recurring payments for this group only
        recurring_payments = RecurringPaymentService.get_all_recurring_payments(group_id=group_id)
        
        payments_data = []
        for payment in recurring_payments:
            participant_ids = payment.get_participant_ids()
            participants = []
            if participant_ids:
                # Only get participants that are members of this group
                participants = [user.name for user in User.query.filter(
                    User.id.in_(participant_ids)
                ).all() if user in group.members]
            
            payments_data.append({
                'id': payment.id,
                'amount': payment.amount,
                'category_id': payment.category_id,
                'category_name': payment.category_obj.name,
                'category_description': payment.category_description,
                'user_id': payment.user_id,
                'user_name': payment.user.name,
                'frequency': payment.frequency,
                'interval_value': payment.interval_value,
                'start_date': payment.start_date.isoformat(),
                'next_due_date': payment.next_due_date.isoformat(),
                'end_date': payment.end_date.isoformat() if payment.end_date else None,
                'is_active': payment.is_active,
                'participant_ids': participant_ids,
                'participants': participants,
                'group_id': payment.group_id,
                'created_at': payment.created_at.isoformat(),
                'last_updated': payment.last_updated.isoformat()
            })
        
        return jsonify({
            'success': True,
            'recurring_payments': payments_data
        })
    
    except Exception as e:
        logger.error(f"Error getting recurring payments for group {group_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading recurring payments'
        }), 500

@recurring.route('/payments/<int:group_id>', methods=['POST'])
def create_recurring_payment_api(group_id):
    """
    Create a new recurring payment for a specific group
    FIXED: Ensures proper group context and balance updates
    """
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.json
        logger.info(f"[CREATE] Received data for recurring payment in group {group_id}: {data}")
        
        # Add group_id to data
        data['group_id'] = group_id
        
        # Validate required fields
        required_fields = ['amount', 'category_id', 'user_id', 'frequency', 'start_date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Convert string IDs to integers for database queries
        try:
            user_id = int(data['user_id'])
            category_id = int(data['category_id'])
            participant_ids = [int(pid) for pid in data.get('participant_ids', [])]
        except (ValueError, TypeError) as e:
            logger.error(f"[CREATE] Error converting IDs to integers: {e}")
            return jsonify({
                'success': False,
                'message': 'Invalid ID format'
            }), 400
        
        # Validate that user is a group member
        payer = User.query.get(user_id)
        if not payer or payer not in group.members:
            return jsonify({
                'success': False,
                'message': 'Payer must be a group member'
            }), 400
        
        # Validate that participants are group members
        if participant_ids:
            participants = User.query.filter(User.id.in_(participant_ids)).all()
            logger.info(f"[CREATE] Found {len(participants)} participants for IDs: {participant_ids}")
            
            for participant in participants:
                if participant not in group.members:
                    return jsonify({
                        'success': False,
                        'message': f'All participants must be group members. {participant.name} is not in this group.'
                    }), 400
        
        # Validate that category exists
        category = Category.query.get(category_id)
        if not category:
            return jsonify({
                'success': False,
                'message': 'Invalid category selected'
            }), 400
        
        # Add "Recurring" to description if not already there
        description = data.get('category_description', '').strip()
        if description:
            if "recurring" not in description.lower():
                description = f"{description} - Recurring"
        else:
            description = "Recurring"
        data['category_description'] = description
        
        logger.info(f"[CREATE] Updated description: {description}")
        logger.info(f"[CREATE] Participant IDs (converted to int): {participant_ids}")
        
        # Create recurring payment using service (includes balance updates)
        recurring_payment = RecurringPaymentService.create_recurring_payment(data)
        
        logger.info(f"[CREATE] Created recurring payment with ID: {recurring_payment.id}")
        
        # FIXED: Force balance recalculation to ensure expenses appear in tables
        try:
            logger.info(f"[CREATE] Forcing balance recalculation for group {group_id}")
            BalanceService.calculate_group_balances(group_id)
            logger.info(f"[CREATE] Balance recalculation completed for group {group_id}")
        except Exception as e:
            logger.warning(f"[CREATE] Balance calculation warning: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment created successfully',
            'recurring_payment_id': recurring_payment.id
        })
    
    except ValueError as e:
        logger.error(f"[CREATE] ValueError creating recurring payment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    
    except Exception as e:
        logger.error(f"[CREATE] Error creating recurring payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error creating recurring payment'
        }), 500

@recurring.route('/payments/<int:group_id>/<int:payment_id>', methods=['PUT'])
def update_recurring_payment_api(group_id, payment_id):
    """Update an existing recurring payment"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        logger.info(f"[UPDATE_ROUTE] PUT request received for payment {payment_id} in group {group_id}")
        
        # Get and validate JSON data
        if not request.is_json:
            logger.error(f"[UPDATE_ROUTE] ERROR: Request is not JSON")
            return jsonify({
                'success': False,
                'message': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        if not data:
            logger.error(f"[UPDATE_ROUTE] ERROR: No JSON data received")
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
            
        logger.info(f"[UPDATE_ROUTE] Received data: {data}")
        
        # Check if recurring payment exists and belongs to the group
        existing_payment = RecurringPayment.query.filter_by(id=payment_id, group_id=group_id).first()
        if not existing_payment:
            logger.error(f"[UPDATE_ROUTE] ERROR: Payment {payment_id} not found in group {group_id}")
            return jsonify({
                'success': False,
                'message': f'Recurring payment {payment_id} not found in this group'
            }), 404
        
        logger.info(f"[UPDATE_ROUTE] Found existing payment: {existing_payment.id}")
        
        # Add "Recurring" to description if provided and not already there
        if 'category_description' in data:
            description = data.get('category_description', '').strip()
            if description:
                if "recurring" not in description.lower():
                    description = f"{description} - Recurring"
            else:
                description = "Recurring"
            data['category_description'] = description
            logger.info(f"[UPDATE_ROUTE] Updated description: {description}")
        
        # Update recurring payment using service
        logger.info(f"[UPDATE_ROUTE] Calling service to update payment {payment_id}")
        recurring_payment = RecurringPaymentService.update_recurring_payment(payment_id, data)
        
        # Commit the changes
        logger.info(f"[UPDATE_ROUTE] Committing changes to database")
        db.session.commit()
        
        logger.info(f"[UPDATE_ROUTE] Successfully updated payment {payment_id}")
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment updated successfully',
            'recurring_payment_id': recurring_payment.id
        }), 200
    
    except ValueError as e:
        db.session.rollback()
        logger.error(f"[UPDATE_ROUTE] ValueError: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"[UPDATE_ROUTE] Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error updating recurring payment: {str(e)}'
        }), 500

@recurring.route('/payments/<int:group_id>/<int:payment_id>', methods=['DELETE'])
def delete_recurring_payment_api(group_id, payment_id):
    """Delete (deactivate) a recurring payment"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Verify payment belongs to group
        payment = RecurringPayment.query.filter_by(id=payment_id, group_id=group_id).first()
        if not payment:
            return jsonify({
                'success': False,
                'message': 'Payment not found in this group'
            }), 404
        
        recurring_payment = RecurringPaymentService.delete_recurring_payment(payment_id)
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting recurring payment: {e}")
        return jsonify({
            'success': False,
            'message': 'Error deleting recurring payment'
        }), 500

@recurring.route('/payments/<int:group_id>/<int:payment_id>/process', methods=['POST'])
def process_recurring_payment_api(group_id, payment_id):
    """
    Manually process a recurring payment to create an expense
    FIXED: Ensures balance updates after manual processing
    """
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        logger.info(f"Processing recurring payment {payment_id} for group {group_id}")
        
        # Verify payment belongs to group
        recurring_payment = RecurringPayment.query.filter_by(id=payment_id, group_id=group_id).first()
        if not recurring_payment:
            return jsonify({
                'success': False,
                'message': 'Payment not found in this group'
            }), 404
        
        if not recurring_payment.is_active:
            return jsonify({
                'success': False,
                'message': 'Cannot process inactive recurring payment'
            }), 400
        
        # Create expense for today regardless of due date
        from models import Expense
        expense_date = date.today()
        
        logger.info(f"Creating expense for date: {expense_date}")
        
        # Check if already processed for today
        existing_expense = Expense.query.filter(
            Expense.recurring_payment_id == recurring_payment.id,
            Expense.date == expense_date,
            Expense.group_id == group_id
        ).first()
        
        if existing_expense:
            return jsonify({
                'success': False,
                'message': 'This recurring payment has already been processed for today'
            }), 400
        
        # Create the expense directly (this now includes balance updates)
        expense = RecurringPaymentService._create_expense_from_recurring_manual(recurring_payment, expense_date)
        
        # Commit the transaction
        db.session.commit()
        
        # FIXED: Ensure balance calculation happens after manual processing
        try:
            logger.info(f"[MANUAL] Updating balances for group {group_id} after manual processing")
            BalanceService.calculate_group_balances(group_id)
            logger.info(f"[MANUAL] Balance update completed for group {group_id}")
        except Exception as e:
            logger.warning(f"[MANUAL] Balance calculation warning: {e}")
        
        logger.info(f"Successfully created expense {expense.id} from recurring payment {payment_id}")
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment processed successfully',
            'expense_id': expense.id
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing recurring payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error processing recurring payment'
        }), 500

@recurring.route('/process-due/<int:group_id>', methods=['POST'])
def process_group_due_payments(group_id):
    """
    Process all due recurring payments for a specific group
    FIXED: Proper balance updates and group context
    """
    group = Group.query.get_or_404(group_id)
    
    # Check user access (or allow system access)
    if current_user.is_authenticated and current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        logger.info(f"[GROUP_PROCESS] Processing due payments for group {group_id} ({group.name})")
        created_expenses = RecurringPaymentService.process_group_due_payments(group_id)
        
        logger.info(f"[GROUP_PROCESS] Created {len(created_expenses)} expenses for group {group_id}")
        
        # FIXED: Force balance recalculation to ensure table updates
        if created_expenses:
            try:
                logger.info(f"[GROUP_PROCESS] Forcing balance recalculation for group {group_id}")
                BalanceService.calculate_group_balances(group_id)
                logger.info(f"[GROUP_PROCESS] Balance recalculation completed")
            except Exception as e:
                logger.warning(f"[GROUP_PROCESS] Balance calculation warning: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(created_expenses)} due recurring payments for group',
            'expenses_created': len(created_expenses),
            'group_id': group_id
        })
    
    except Exception as e:
        logger.error(f"Error processing due payments for group {group_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error processing due payments'
        }), 500

@recurring.route('/process-due', methods=['POST'])
def process_all_due_payments():
    """
    Process all due recurring payments (for background job) - processes all groups
    FIXED: Proper logging and balance updates for all groups
    """
    try:
        logger.info("[SYSTEM] Starting system-wide recurring payment processing")
        created_expenses = RecurringPaymentService.process_due_payments()
        
        logger.info(f"[SYSTEM] System-wide processing completed: {len(created_expenses)} expenses created")
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(created_expenses)} due recurring payments across all groups',
            'expenses_created': len(created_expenses)
        })
    
    except Exception as e:
        logger.error(f"[SYSTEM] Error in system-wide processing: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error processing due payments'
        }), 500

# FIXED: Add an admin endpoint for wake-and-process (for GitHub Actions)
@recurring.route('/admin/wake-and-process', methods=['POST'])
def admin_wake_and_process():
    """
    Admin endpoint for GitHub Actions to wake app and process all due payments
    FIXED: Better logging and response format
    """
    try:
        logger.info("[ADMIN] Admin wake-and-process endpoint called")
        
        # Get request info for logging
        request_data = request.get_json() or {}
        source = request_data.get('source', 'unknown')
        timestamp = request_data.get('timestamp', datetime.now().isoformat())
        
        logger.info(f"[ADMIN] Source: {source}, Timestamp: {timestamp}")
        
        # Process all due recurring payments
        created_expenses = RecurringPaymentService.process_due_payments()
        
        logger.info(f"[ADMIN] Processing completed: {len(created_expenses)} expenses created")
        
        # Build response with details
        response_data = {
            'success': True,
            'message': f'Wake and process completed successfully',
            'expenses_created': len(created_expenses),
            'source': source,
            'timestamp': timestamp,
            'processed_at': datetime.now().isoformat()
        }
        
        # Add expense details if any were created
        if created_expenses:
            response_data['expense_details'] = [
                {
                    'id': exp.id,
                    'amount': float(exp.amount),
                    'group_id': exp.group_id,
                    'date': exp.date.isoformat(),
                    'description': exp.category_description
                }
                for exp in created_expenses[:10]  # Limit to first 10 for response size
            ]
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"[ADMIN] Error in wake-and-process: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error in wake and process: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500