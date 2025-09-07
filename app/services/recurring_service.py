"""
Service for handling recurring payment logic
"""
from datetime import datetime, date, timedelta
from models import db, RecurringPayment, Expense, ExpenseParticipant, User, Category
from balance_service import BalanceService
import json


class RecurringPaymentService:
    
    @staticmethod
    def process_due_payments(check_date=None):
        """
        Check for due recurring payments and create expense records
        Returns list of created expenses
        """
        if check_date is None:
            check_date = datetime.now().date()
        
        # Get all active recurring payments that are due
        due_payments = RecurringPayment.query.filter(
            RecurringPayment.is_active == True,
            RecurringPayment.next_due_date <= check_date
        ).all()
        
        created_expenses = []
        
        for recurring_payment in due_payments:
            # Check if end date has passed
            if recurring_payment.end_date and check_date > recurring_payment.end_date:
                recurring_payment.is_active = False
                continue
            
            # Check if we already created an expense for this due date
            existing_expense = Expense.query.filter(
                Expense.recurring_payment_id == recurring_payment.id,
                Expense.date == recurring_payment.next_due_date
            ).first()
            
            if existing_expense:
                # Already processed this due date, just update next_due_date
                recurring_payment.next_due_date = recurring_payment.calculate_next_due_date()
                continue
            
            # Create new expense from recurring payment
            expense = RecurringPaymentService._create_expense_from_recurring(recurring_payment)
            created_expenses.append(expense)
            
            # Update next due date
            recurring_payment.next_due_date = recurring_payment.calculate_next_due_date()
            recurring_payment.last_updated = datetime.utcnow()
        
        db.session.commit()
        return created_expenses
    
    @staticmethod
    def _create_expense_from_recurring(recurring_payment):
        """Create an expense record from a recurring payment"""
        # Create the expense
        expense = Expense(
            amount=recurring_payment.amount,
            category_id=recurring_payment.category_id,
            category_description=recurring_payment.category_description,
            user_id=recurring_payment.user_id,
            date=recurring_payment.next_due_date,
            split_type='equal',
            recurring_payment_id=recurring_payment.id
        )
        
        db.session.add(expense)
        db.session.flush()  # Get the expense ID
        
        # Add participants
        participant_ids = recurring_payment.get_participant_ids()
        if not participant_ids:
            # If no participants specified, use all users
            participant_ids = [user.id for user in User.query.all()]
        
        amount_per_person = recurring_payment.amount / len(participant_ids)
        
        for user_id in participant_ids:
            participant = ExpenseParticipant(
                expense_id=expense.id,
                user_id=user_id,
                amount_owed=amount_per_person
            )
            db.session.add(participant)
        
        # Update balances

        return expense
    
    @staticmethod
    def create_recurring_payment(data):
        """Create a new recurring payment"""
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        current_date = datetime.now().date()
        
        recurring_payment = RecurringPayment(
            amount=float(data['amount']),
            category_id=int(data['category_id']),
            category_description=data.get('category_description', ''),
            user_id=int(data['user_id']),
            frequency=data['frequency'],
            interval_value=int(data.get('interval_value', 1)),
            start_date=start_date,
            next_due_date=start_date,
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            is_active=True
        )
        
        # Set participants
        participant_ids = data.get('participant_ids', [])
        recurring_payment.set_participant_ids([int(id) for id in participant_ids])
        
        db.session.add(recurring_payment)
        db.session.flush()  # Get the ID
        
        # If start date is in the past, create expenses up to current date
        if start_date < current_date:
            RecurringPaymentService._create_past_expenses(recurring_payment, current_date)
        
        db.session.commit()
        return recurring_payment
    
    @staticmethod
    def _create_past_expenses(recurring_payment, current_date):
        """Create expenses for past due dates"""
        created_expenses = []
        check_date = recurring_payment.start_date
        
        while check_date <= current_date:
            # Check if expense already exists for this date
            existing_expense = Expense.query.filter(
                Expense.recurring_payment_id == recurring_payment.id,
                Expense.date == check_date
            ).first()
            
            if not existing_expense:
                # Create expense for this date
                expense = Expense(
                    amount=recurring_payment.amount,
                    category_id=recurring_payment.category_id,
                    category_description=recurring_payment.category_description,
                    user_id=recurring_payment.user_id,
                    date=check_date,
                    split_type='equal',
                    recurring_payment_id=recurring_payment.id
                )
                
                db.session.add(expense)
                db.session.flush()
                
                # Add participants
                participant_ids = recurring_payment.get_participant_ids()
                if not participant_ids:
                    participant_ids = [user.id for user in User.query.all()]
                
                amount_per_person = recurring_payment.amount / len(participant_ids)
                
                for user_id in participant_ids:
                    participant = ExpenseParticipant(
                        expense_id=expense.id,
                        user_id=user_id,
                        amount_owed=amount_per_person
                    )
                    db.session.add(participant)
                
                # Update balances
            
                created_expenses.append(expense)
            
            # Calculate next date
            if recurring_payment.frequency == 'daily':
                check_date = check_date + timedelta(days=recurring_payment.interval_value)
            elif recurring_payment.frequency == 'weekly':
                check_date = check_date + timedelta(weeks=recurring_payment.interval_value)
            elif recurring_payment.frequency == 'monthly':
                from dateutil.relativedelta import relativedelta
                check_date = check_date + relativedelta(months=recurring_payment.interval_value)
            elif recurring_payment.frequency == 'yearly':
                from dateutil.relativedelta import relativedelta
                check_date = check_date + relativedelta(years=recurring_payment.interval_value)
            else:
                break  # Unknown frequency
        
        # Set next due date to the next occurrence after current date
        recurring_payment.next_due_date = check_date
        
        return created_expenses
    
    @staticmethod
    def update_recurring_payment(recurring_payment_id, data):
        """Update an existing recurring payment"""
        recurring_payment = RecurringPayment.query.get_or_404(recurring_payment_id)
        
        
        recurring_payment.amount = float(data['amount'])
        recurring_payment.category_id = int(data['category_id'])
        recurring_payment.category_description = data.get('category_description', '')
        recurring_payment.user_id = int(data['user_id'])
        recurring_payment.frequency = data['frequency']
        recurring_payment.interval_value = int(data.get('interval_value', 1))
        recurring_payment.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None
        recurring_payment.is_active = data.get('is_active', True)
        recurring_payment.last_updated = datetime.utcnow()
        
        # Update participants
        participant_ids = data.get('participant_ids', [])
        recurring_payment.set_participant_ids([int(id) for id in participant_ids])
        
        # Update next due date if provided
        if 'next_due_date' in data and data['next_due_date']:
            recurring_payment.next_due_date = datetime.strptime(data['next_due_date'], '%Y-%m-%d').date()
        
        # If start date changed, recalculate next due date
        if 'start_date' in data:
            new_start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if new_start_date != recurring_payment.start_date:
                recurring_payment.start_date = new_start_date
                # Only update next_due_date if it hasn't been processed yet
                if recurring_payment.next_due_date >= new_start_date:
                    recurring_payment.next_due_date = new_start_date
        
        # DON'T commit here - let the route handle it
        return recurring_payment
    
    @staticmethod
    def delete_recurring_payment(recurring_payment_id):
        """Delete a recurring payment"""
        recurring_payment = RecurringPayment.query.get_or_404(recurring_payment_id)
        
        # Mark as inactive instead of deleting to preserve history
        recurring_payment.is_active = False
        recurring_payment.last_updated = datetime.utcnow()
        
        db.session.commit()
        return recurring_payment
    
    @staticmethod
    def get_all_recurring_payments():
        """Get all recurring payments with user and category info"""
        return RecurringPayment.query.join(User).join(Category).all()
    
    @staticmethod
    def get_recurring_payment_with_participants(recurring_payment_id):
        """Get recurring payment with participant details"""
        recurring_payment = RecurringPayment.query.get_or_404(recurring_payment_id)
        participant_ids = recurring_payment.get_participant_ids()
        participants = User.query.filter(User.id.in_(participant_ids)).all() if participant_ids else []
        
        return {
            'recurring_payment': recurring_payment,
            'participants': participants
        }