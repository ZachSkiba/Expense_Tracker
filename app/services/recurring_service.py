"""
Service for handling recurring payment logic - FIXED VERSION V2
Creates past expenses and fixes update logic
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
        # Ensure description has "Recurring" in it
        description = recurring_payment.category_description or ""
        if description and not description.lower().endswith('recurring'):
            description = f"{description} - Recurring"
        elif not description:
            description = "Recurring"
        
        # Create the expense
        expense = Expense(
            amount=recurring_payment.amount,
            category_id=recurring_payment.category_id,
            category_description=description,
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
        
        return expense
    
    @staticmethod
    def _create_expense_from_recurring_manual(recurring_payment, expense_date):
        """Create an expense record from a recurring payment for manual processing"""
        # Ensure description has "Recurring" in it
        description = recurring_payment.category_description or ""
        if description.strip() and "recurring" not in description.lower():
            description = f"{description} - Recurring"
        elif not description.strip():
            description = "Recurring"
        
        # Create the expense
        expense = Expense(
            amount=recurring_payment.amount,
            category_id=recurring_payment.category_id,
            category_description=description,
            user_id=recurring_payment.user_id,
            date=expense_date,
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
        
        return expense
    
    @staticmethod
    def create_recurring_payment(data):
        """Create a new recurring payment - WITH PAST EXPENSE CREATION"""
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        current_date = datetime.now().date()
        
        print(f"[CREATE] Start date: {start_date}, Current date: {current_date}")
        
        # Ensure description has "Recurring" in it (already handled in route, but double-check)
        description = data.get('category_description', '').strip()
        if description and not description.lower().endswith('recurring'):
            description = f"{description} - Recurring"
        elif not description:
            description = "Recurring"
        
        recurring_payment = RecurringPayment(
            amount=float(data['amount']),
            category_id=int(data['category_id']),
            category_description=description,
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
            print(f"[CREATE] Start date is in past, creating past expenses")
            RecurringPaymentService._create_past_expenses(recurring_payment, current_date)
        
        db.session.commit()
        return recurring_payment
    
    @staticmethod
    def _create_past_expenses(recurring_payment, current_date):
        """Create expenses for past due dates and set correct next_due_date"""
        created_expenses = []
        check_date = recurring_payment.start_date
        
        print(f"[PAST_EXPENSES] Creating from {check_date} to {current_date}")
        
        while check_date <= current_date:
            print(f"[PAST_EXPENSES] Checking date: {check_date}")
            
            # Check if expense already exists for this date
            existing_expense = Expense.query.filter(
                Expense.recurring_payment_id == recurring_payment.id,
                Expense.date == check_date
            ).first()
            
            if not existing_expense:
                print(f"[PAST_EXPENSES] Creating expense for {check_date}")
                
                # Ensure description has "Recurring" in it
                description = recurring_payment.category_description or ""
                if description and not description.lower().endswith('recurring'):
                    description = f"{description} - Recurring"
                elif not description:
                    description = "Recurring"
                
                # Create expense for this date
                expense = Expense(
                    amount=recurring_payment.amount,
                    category_id=recurring_payment.category_id,
                    category_description=description,
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
            
                created_expenses.append(expense)
                print(f"[PAST_EXPENSES] Created expense {expense.id} for {check_date}")
            else:
                print(f"[PAST_EXPENSES] Expense already exists for {check_date}")
            
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
                print(f"[PAST_EXPENSES] Unknown frequency: {recurring_payment.frequency}")
                break  # Unknown frequency
        
        # Set next due date to the next occurrence after current date
        recurring_payment.next_due_date = check_date
        print(f"[PAST_EXPENSES] Set next_due_date to: {check_date}")
        
        return created_expenses
    
    @staticmethod
    def update_recurring_payment(recurring_payment_id, data):
        """Update an existing recurring payment - FIXED VERSION"""
        # Get the existing recurring payment
        recurring_payment = RecurringPayment.query.get_or_404(recurring_payment_id)
        
        print(f"[UPDATE_SERVICE] Updating recurring payment {recurring_payment_id}")
        print(f"[UPDATE_SERVICE] Received data: {data}")
        
        # Update fields from data
        if 'amount' in data:
            recurring_payment.amount = float(data['amount'])
            print(f"[UPDATE_SERVICE] Updated amount to: {recurring_payment.amount}")
        
        if 'category_id' in data:
            recurring_payment.category_id = int(data['category_id'])
            print(f"[UPDATE_SERVICE] Updated category_id to: {recurring_payment.category_id}")
        
        if 'category_description' in data:
            description = data['category_description'].strip()
            if description and "recurring" not in description.lower():
                description = f"{description} - Recurring"
            elif not description:
                description = "Recurring"
            recurring_payment.category_description = description
            print(f"[UPDATE_SERVICE] Updated description to: {description}")
        
        if 'user_id' in data:
            recurring_payment.user_id = int(data['user_id'])
            print(f"[UPDATE_SERVICE] Updated user_id to: {recurring_payment.user_id}")
        
        if 'frequency' in data:
            recurring_payment.frequency = data['frequency']
            print(f"[UPDATE_SERVICE] Updated frequency to: {recurring_payment.frequency}")
        
        if 'interval_value' in data:
            recurring_payment.interval_value = int(data.get('interval_value', 1))
            print(f"[UPDATE_SERVICE] Updated interval_value to: {recurring_payment.interval_value}")
        
        if 'end_date' in data:
            if data['end_date']:
                recurring_payment.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            else:
                recurring_payment.end_date = None
            print(f"[UPDATE_SERVICE] Updated end_date to: {recurring_payment.end_date}")
        
        if 'is_active' in data:
            # Handle both boolean and string values
            if isinstance(data['is_active'], bool):
                recurring_payment.is_active = data['is_active']
            else:
                recurring_payment.is_active = str(data['is_active']).lower() == 'true'
            print(f"[UPDATE_SERVICE] Updated is_active to: {recurring_payment.is_active}")
        
        if 'next_due_date' in data and data['next_due_date']:
            recurring_payment.next_due_date = datetime.strptime(data['next_due_date'], '%Y-%m-%d').date()
            print(f"[UPDATE_SERVICE] Updated next_due_date to: {recurring_payment.next_due_date}")
        
        if 'start_date' in data:
            new_start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if new_start_date != recurring_payment.start_date:
                recurring_payment.start_date = new_start_date
                # Only update next_due_date if it hasn't been processed yet
                if recurring_payment.next_due_date >= new_start_date:
                    recurring_payment.next_due_date = new_start_date
                print(f"[UPDATE_SERVICE] Updated start_date to: {recurring_payment.start_date}")
        
        # Update participants
        if 'participant_ids' in data:
            participant_ids = data['participant_ids']
            recurring_payment.set_participant_ids([int(id) for id in participant_ids])
            print(f"[UPDATE_SERVICE] Updated participant_ids to: {participant_ids}")
        
        # Update timestamp
        recurring_payment.last_updated = datetime.utcnow()
        
        print(f"[UPDATE_SERVICE] Successfully updated recurring payment {recurring_payment_id}")
        
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