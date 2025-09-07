"""
Blueprint for recurring payments management
"""
from flask import Blueprint, request, jsonify
from models import db, RecurringPayment, User, Category
from app.services.recurring_service import RecurringPaymentService  # Fixed import path
from datetime import datetime

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
                'name': payment.name,
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
            'name': payment.name,
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
        
        # Validate required fields
        required_fields = ['name', 'amount', 'category_id', 'user_id', 'frequency', 'start_date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Create recurring payment using service
        recurring_payment = RecurringPaymentService.create_recurring_payment(data)
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment created successfully',
            'recurring_payment_id': recurring_payment.id
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    
    except Exception as e:
        print(f"Error creating recurring payment: {e}")
        return jsonify({
            'success': False,
            'message': 'Error creating recurring payment'
        }), 500

@recurring.route('/payments/<int:payment_id>', methods=['PUT'])
def update_recurring_payment_api(payment_id):
    """Update an existing recurring payment"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'amount', 'category_id', 'user_id', 'frequency']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Update recurring payment using service
        recurring_payment = RecurringPaymentService.update_recurring_payment(payment_id, data)
        
        return jsonify({
            'success': True,
            'message': 'Recurring payment updated successfully',
            'recurring_payment_id': recurring_payment.id
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    
    except Exception as e:
        print(f"Error updating recurring payment: {e}")
        return jsonify({
            'success': False,
            'message': 'Error updating recurring payment'
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
    """Manually process a recurring payment to create an expense"""
    try:
        recurring_payment = RecurringPayment.query.get_or_404(payment_id)
        
        if not recurring_payment.is_active:
            return jsonify({
                'success': False,
                'message': 'Cannot process inactive recurring payment'
            }), 400
        
        # Check if already processed for current due date
        from models import Expense
        existing_expense = Expense.query.filter(
            Expense.recurring_payment_id == recurring_payment.id,
            Expense.date == recurring_payment.next_due_date
        ).first()
        
        if existing_expense:
            return jsonify({
                'success': False,
                'message': 'This recurring payment has already been processed for the current due date'
            }), 400
        
        # Process the payment
        created_expenses = RecurringPaymentService.process_due_payments()
        
        # Find the expense that was created for this payment
        created_expense = None
        for expense in created_expenses:
            if expense.recurring_payment_id == payment_id:
                created_expense = expense
                break
        
        if created_expense:
            return jsonify({
                'success': True,
                'message': 'Recurring payment processed successfully',
                'expense_id': created_expense.id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No expense was created. Payment may not be due yet.'
            }), 400
    
    except Exception as e:
        print(f"Error processing recurring payment: {e}")
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