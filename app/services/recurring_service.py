"""
Service for handling recurring payment logic - UNIFIED VERSION
Both startup processor and regular service now use the same comprehensive logic
"""
from datetime import datetime, date, timedelta
from models import db, RecurringPayment, Expense, ExpenseParticipant, User, Category
from balance_service import BalanceService
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

class RecurringPaymentService:
    
    @staticmethod
    def process_due_payments(check_date=None):
        """
        UNIFIED: Check for due recurring payments and create expense records
        Uses the same comprehensive logic as startup processor
        """
        if check_date is None:
            check_date = datetime.now().date()
        
        logger.info(f"🔄 PROCESSING: Checking for due/overdue recurring payments up to {check_date}...")
        
        # Get all active recurring payments that are due or overdue
        due_payments = RecurringPayment.query.filter(
            RecurringPayment.is_active == True,
            RecurringPayment.next_due_date <= check_date
        ).all()
        
        if not due_payments:
            logger.info("✅ PROCESSING: No due or overdue recurring payments found")
            return []
        
        logger.info(f"📋 PROCESSING: Found {len(due_payments)} payments to check:")
        
        created_expenses = []
        processed_count = 0
        skipped_count = 0
        
        for recurring_payment in due_payments:
            days_diff = (check_date - recurring_payment.next_due_date).days
            status = "due today" if days_diff == 0 else f"overdue by {days_diff} days"
            
            logger.info(f"   🔍 Checking: {recurring_payment.category_obj.name} - ${recurring_payment.amount} ({status})")
            
            # Process ALL missed dates from next_due_date up through check_date
            current_due_date = recurring_payment.next_due_date
            payment_expenses = []
            
            while current_due_date <= check_date:
                # Check if expense already exists for this date
                existing_expense = Expense.query.filter(
                    Expense.recurring_payment_id == recurring_payment.id,
                    Expense.date == current_due_date
                ).first()
                
                if existing_expense:
                    logger.info(f"      ⏭️  Skipped: Expense #{existing_expense.id} already exists for {current_due_date}")
                    skipped_count += 1
                else:
                    # Create expense for this date
                    logger.info(f"      ✨ Creating expense for {current_due_date}...")
                    
                    try:
                        expense = RecurringPaymentService._create_expense_for_date(
                            recurring_payment, 
                            current_due_date
                        )
                        
                        payment_expenses.append(expense)
                        created_expenses.append(expense)
                        
                        logger.info(f"      ✅ Created expense #{expense.id} for ${expense.amount}")
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(f"      ❌ Error creating expense for {current_due_date}: {e}")
                        continue
                
                # Calculate next occurrence
                old_due_date = current_due_date
                current_due_date = recurring_payment.calculate_next_due_date(old_due_date)
                
                # Safety check to prevent infinite loops
                if current_due_date <= old_due_date:
                    logger.error(f"      ⚠️  Date calculation error: {old_due_date} -> {current_due_date}")
                    break
            
            # After processing all valid dates, check if payment should be deactivated
            if recurring_payment.end_date and current_due_date > recurring_payment.end_date:
                # Payment has ended - deactivate it and clear next_due_date
                recurring_payment.is_active = False
                recurring_payment.next_due_date = None  # Set to NULL to indicate completion
                recurring_payment.last_updated = datetime.utcnow()
                logger.info(f"      🔚 Payment ended on {recurring_payment.end_date}, marked as inactive with next_due_date cleared")
            else:
                # Update the recurring payment's next_due_date to the next future date
                old_next_due = recurring_payment.next_due_date
                recurring_payment.next_due_date = current_due_date
                recurring_payment.last_updated = datetime.utcnow()
                
                if payment_expenses:
                    logger.info(f"      📅 Updated next due date: {old_next_due} → {recurring_payment.next_due_date}")
        
        # Commit all changes
        if processed_count > 0 or skipped_count > 0:
            db.session.commit()
            logger.info(f"✅ PROCESSING: Processed {processed_count} payments, skipped {skipped_count} (already existed)")
        else:
            logger.info("ℹ️  PROCESSING: No changes made")
        
        return created_expenses
    
    @staticmethod
    def _create_expense_for_date(recurring_payment, expense_date):
        """
        Create an expense record from a recurring payment for a specific date
        UNIFIED logic used by both startup and regular processing
        """
        # Ensure description has "Recurring" in it
        description = recurring_payment.category_description or ""
        if description.strip() and "recurring" not in description.lower():
            description = f"{description} - Recurring"
        elif not description.strip():
            description = "Recurring"
        
        logger.info(f"         Creating expense with description: '{description}'")
        
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
        
        logger.info(f"         Added expense to session with ID: {expense.id}")
        
        # Add participants
        participant_ids = recurring_payment.get_participant_ids()
        if not participant_ids:
            # If no participants specified, use all users
            participant_ids = [user.id for user in User.query.all()]
            logger.info(f"         No specific participants, using all users: {participant_ids}")
        else:
            logger.info(f"         Using specified participants: {participant_ids}")
        
        amount_per_person = recurring_payment.amount / len(participant_ids)
        logger.info(f"         Amount per person: ${amount_per_person:.2f}")
        
        for user_id in participant_ids:
            participant = ExpenseParticipant(
                expense_id=expense.id,
                user_id=user_id,
                amount_owed=amount_per_person
            )
            db.session.add(participant)
            logger.info(f"         Added participant: user {user_id}, owes ${amount_per_person:.2f}")
        
        return expense
    
    # Keep the old methods for backward compatibility, but they now use the unified logic
    @staticmethod
    def _create_expense_from_recurring(recurring_payment):
        """Legacy method - now uses unified logic for today's date"""
        return RecurringPaymentService._create_expense_for_date(recurring_payment, recurring_payment.next_due_date)
    
    @staticmethod
    def _create_expense_from_recurring_manual(recurring_payment, expense_date):
        """Legacy method - now uses unified logic"""
        return RecurringPaymentService._create_expense_for_date(recurring_payment, expense_date)
    
    @staticmethod
    def create_recurring_payment(data):
        """Create a new recurring payment - WITH COMPREHENSIVE PAST EXPENSE CREATION"""
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        current_date = datetime.now().date()
        
        logger.info(f"[CREATE] Start date: {start_date}, Current date: {current_date}")
        
        # Ensure description has "Recurring" in it
        description = data.get('category_description', '').strip()
        if description and "recurring" not in description.lower():
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
        
        # If start date is in the past, use the unified processing logic
        if start_date < current_date:
            logger.info(f"[CREATE] Start date is in past, processing due payments through today")
            # Temporarily commit the recurring payment so process_due_payments can find it
            db.session.commit()
            
            # Use the same unified logic to create all past expenses
            created_expenses = RecurringPaymentService.process_due_payments(current_date)
            logger.info(f"[CREATE] Created {len(created_expenses)} past expenses")
        else:
            db.session.commit()
        
        return recurring_payment
    
    @staticmethod
    def update_recurring_payment(recurring_payment_id, data):
        """Update an existing recurring payment"""
        recurring_payment = RecurringPayment.query.get_or_404(recurring_payment_id)
        
        logger.info(f"[UPDATE_SERVICE] Updating recurring payment {recurring_payment_id}")
        
        # Update fields from data
        if 'amount' in data:
            recurring_payment.amount = float(data['amount'])
        
        if 'category_id' in data:
            recurring_payment.category_id = int(data['category_id'])
        
        if 'category_description' in data:
            description = data['category_description'].strip()
            if description and "recurring" not in description.lower():
                description = f"{description} - Recurring"
            elif not description:
                description = "Recurring"
            recurring_payment.category_description = description
        
        if 'user_id' in data:
            recurring_payment.user_id = int(data['user_id'])
        
        if 'frequency' in data:
            recurring_payment.frequency = data['frequency']
        
        if 'interval_value' in data:
            recurring_payment.interval_value = int(data.get('interval_value', 1))
        
        if 'end_date' in data:
            if data['end_date']:
                recurring_payment.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            else:
                recurring_payment.end_date = None
        
        if 'is_active' in data:
            if isinstance(data['is_active'], bool):
                recurring_payment.is_active = data['is_active']
            else:
                recurring_payment.is_active = str(data['is_active']).lower() == 'true'
        
        if 'next_due_date' in data and data['next_due_date']:
            recurring_payment.next_due_date = datetime.strptime(data['next_due_date'], '%Y-%m-%d').date()
        
        if 'start_date' in data:
            new_start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if new_start_date != recurring_payment.start_date:
                recurring_payment.start_date = new_start_date
                if recurring_payment.next_due_date >= new_start_date:
                    recurring_payment.next_due_date = new_start_date
        
        # Update participants
        if 'participant_ids' in data:
            participant_ids = data['participant_ids']
            recurring_payment.set_participant_ids([int(id) for id in participant_ids])
        
        # Update timestamp
        recurring_payment.last_updated = datetime.utcnow()
        
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