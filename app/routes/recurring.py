"""
Blueprint for recurring payments management - DEBUG VERSION
Add better error handling and logging for PUT requests
"""
from flask import Blueprint, request, jsonify
from models import db, RecurringPayment, User, Category
from app.services.recurring_service import RecurringPaymentService
from datetime import datetime, date

recurring = Blueprint('recurring', __name__, url_prefix='/api/recurring')

@recurring.route('/payments', methods=['GET'])
def get_recurring_payments_api():
    """Get all recurring payments with details"""
    try:
        recurring_payments = RecurringPayment.query.join(User).join(Category).filter(
            RecurringPayment.is_active == True
        ).all()
        
        payments_data = []
        for payment in recurring_payments:
            participant_ids = payment.get_participant_ids()
            participants = []
            if participant_ids:
                participants = [user.name for user in User.query.filter(User.id.in_(participant_ids)).all()]
            
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
                'created_at': payment.created_at.isoformat(),
                'last_updated': payment.last_updated.isoformat()
            })
        
        return jsonify({
            'success': True,
            'recurring_payments': payments_data
        })
    
    except Exception as e:
        print(f"Error getting recurring payments: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading recurring payments'
        }), 500

@recurring.route('/payments/<int:payment_id>', methods=['GET'])
def get_recurring_payment_api(payment_id):
    """Get a specific recurring payment"""
    try:
        payment = RecurringPayment.query.get_or_404(payment_id)
        
        participant_ids = payment.get_participant_ids()
        participants = []
        if participant_ids:
            participants = [{'id': user.id, 'name': user.name} for user in User.query.filter(User.id.in_(participant_ids)).all()]
        
        payment_data = {
            'id': payment.id,
            'amount': payment.amount,
            'category_id': payment.category_id,
            'category_description': payment.category_description,
            'user_id': payment.user_id,
            'frequency': payment.frequency,
            'interval_value': payment.interval_value,
            'start_date': payment.start_date.isoformat(),
            'next_due_date': payment.next_due_date.isoformat(),
            'end_date': payment.end_date.isoformat() if payment.end_date else None,
            'is_active': payment.is_active,
            'participant_ids': participant_ids,
            'participants': participants
        }
        
        return jsonify({
            'success': True,
            'recurring_payment': payment_data
        })
    
    except Exception as e:
        print(f"Error getting recurring payment: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading recurring payment'
        }), 500

@recurring.route('/payments', methods=['POST'])
def recurring_payments_api():
    """Create a new recurring payment"""
    try:
        data = request.json
        print(f"[CREATE] Received data for recurring payment: {data}")  # Debug log
        
        # Validate required fields
        required_fields = ['amount', 'category_id', 'user_id', 'frequency', 'start_date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Add "Recurring" to description if not already there
        description = data.get('category_description', '').strip()
        if description:
            if "recurring" not in description.lower():
                description = f"{description} - Recurring"
        else:
            description = "Recurring"
        data['category_description'] = description
        
        print(f"[CREATE] Updated description: {description}")  # Debug log
        
        # Create recurring payment using service
        recurring_payment = RecurringPaymentService.create_recurring_payment(data)
        
        print(f"[CREATE] Created recurring payment with ID: {recurring_payment.id}")  # Debug log
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment created successfully',
            'recurring_payment_id': recurring_payment.id
        })
    
    except ValueError as e:
        print(f"[CREATE] ValueError creating recurring payment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    
    except Exception as e:
        print(f"[CREATE] Error creating recurring payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error creating recurring payment'
        }), 500

@recurring.route('/payments/<int:payment_id>', methods=['PUT'])
def update_recurring_payment_api(payment_id):
    """Update an existing recurring payment"""
    try:
        # Log the incoming request
        print(f"[UPDATE_ROUTE] PUT request received for payment {payment_id}")
        print(f"[UPDATE_ROUTE] Content-Type: {request.content_type}")
        print(f"[UPDATE_ROUTE] Request method: {request.method}")
        
        # Get and validate JSON data
        if not request.is_json:
            print(f"[UPDATE_ROUTE] ERROR: Request is not JSON")
            return jsonify({
                'success': False,
                'message': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        if not data:
            print(f"[UPDATE_ROUTE] ERROR: No JSON data received")
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
            
        print(f"[UPDATE_ROUTE] Received data: {data}")
        
        # Check if recurring payment exists
        existing_payment = RecurringPayment.query.get(payment_id)
        if not existing_payment:
            print(f"[UPDATE_ROUTE] ERROR: Payment {payment_id} not found")
            return jsonify({
                'success': False,
                'message': f'Recurring payment {payment_id} not found'
            }), 404
        
        print(f"[UPDATE_ROUTE] Found existing payment: {existing_payment.id}")
        
        # Add "Recurring" to description if provided and not already there
        if 'category_description' in data:
            description = data.get('category_description', '').strip()
            if description:
                if "recurring" not in description.lower():
                    description = f"{description} - Recurring"
            else:
                description = "Recurring"
            data['category_description'] = description
            print(f"[UPDATE_ROUTE] Updated description: {description}")
        
        # Update recurring payment using service
        print(f"[UPDATE_ROUTE] Calling service to update payment {payment_id}")
        recurring_payment = RecurringPaymentService.update_recurring_payment(payment_id, data)
        
        # Commit the changes
        print(f"[UPDATE_ROUTE] Committing changes to database")
        db.session.commit()
        
        print(f"[UPDATE_ROUTE] Successfully updated payment {payment_id}")
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment updated successfully',
            'recurring_payment_id': recurring_payment.id
        }), 200
    
    except ValueError as e:
        db.session.rollback()
        print(f"[UPDATE_ROUTE] ValueError: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    
    except Exception as e:
        db.session.rollback()
        print(f"[UPDATE_ROUTE] Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error updating recurring payment: {str(e)}'
        }), 500

@recurring.route('/payments/<int:payment_id>', methods=['DELETE'])
def delete_recurring_payment_api(payment_id):
    """Delete (deactivate) a recurring payment"""
    try:
        recurring_payment = RecurringPaymentService.delete_recurring_payment(payment_id)
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment deleted successfully'
        })
    
    except Exception as e:
        print(f"Error deleting recurring payment: {e}")
        return jsonify({
            'success': False,
            'message': 'Error deleting recurring payment'
        }), 500

@recurring.route('/payments/<int:payment_id>/process', methods=['POST'])
def process_recurring_payment_api(payment_id):
    """Manually process a recurring payment to create an expense - WORKS REGARDLESS OF DUE DATE"""
    try:
        print(f"Processing recurring payment {payment_id}")
        
        recurring_payment = RecurringPayment.query.get_or_404(payment_id)
        
        if not recurring_payment.is_active:
            return jsonify({
                'success': False,
                'message': 'Cannot process inactive recurring payment'
            }), 400
        
        # Create expense for today regardless of due date
        from models import Expense
        expense_date = date.today()
        
        print(f"Creating expense for date: {expense_date}")
        
        # Check if already processed for today
        existing_expense = Expense.query.filter(
            Expense.recurring_payment_id == recurring_payment.id,
            Expense.date == expense_date
        ).first()
        
        if existing_expense:
            return jsonify({
                'success': False,
                'message': 'This recurring payment has already been processed for today'
            }), 400
        
        # Create the expense directly
        expense = RecurringPaymentService._create_expense_from_recurring_manual(recurring_payment, expense_date)
        
        # Commit the transaction
        db.session.commit()
        
        print(f"Successfully created expense {expense.id} from recurring payment {payment_id}")
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment processed successfully',
            'expense_id': expense.id
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error processing recurring payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error processing recurring payment'
        }), 500

@recurring.route('/process-due', methods=['POST'])
def process_all_due_payments():
    """Process all due recurring payments (for background job)"""
    try:
        created_expenses = RecurringPaymentService.process_due_payments()
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(created_expenses)} due recurring payments',
            'expenses_created': len(created_expenses)
        })
    
    except Exception as e:
        print(f"Error processing due payments: {e}")
        return jsonify({
            'success': False,
            'message': 'Error processing due payments'
        }), 500