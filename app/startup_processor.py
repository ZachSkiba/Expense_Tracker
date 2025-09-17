"""
Startup processor for recurring payments - FIXED to not auto-add new users
"""

import logging
from datetime import datetime, date, timedelta
from models import db, RecurringPayment, Expense

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StartupRecurringProcessor:
    """Process missed and due recurring payments on app startup"""
    
    @staticmethod
    def process_startup_recurring_payments(app):
        """
        Process any recurring payments that are due or overdue on app startup
        FIXED: Now properly handles end dates with sentinel dates and inactive status
        """
        with app.app_context():
            try:
                logger.info("🚀 STARTUP: Checking for due/overdue recurring payments...")
                
                today = date.today()
                
                # Get all active recurring payments that are due or overdue
                due_and_overdue = RecurringPayment.query.filter(
                    RecurringPayment.is_active == True,
                    RecurringPayment.next_due_date <= today
                ).all()
                
                if not due_and_overdue:
                    logger.info("✅ STARTUP: No due or overdue recurring payments found")
                    return
                
                logger.info(f"📋 STARTUP: Found {len(due_and_overdue)} payments to check:")
                
                processed_count = 0
                skipped_count = 0
                
                for payment in due_and_overdue:
                    days_diff = (today - payment.next_due_date).days
                    status = "due today" if days_diff == 0 else f"overdue by {days_diff} days"
                    
                    logger.info(f"   🔍 Checking: {payment.category_obj.name} - ${payment.amount} ({status})")
                    
                    # Process ALL missed dates from next_due_date up through today
                    # BUT respect the end_date if it exists
                    current_due_date = payment.next_due_date
                    payment_expenses = []
                    
                    # FIXED: Process expenses while respecting end_date
                    while current_due_date <= today:
                        # CRITICAL: Check if current_due_date is beyond end_date BEFORE processing
                        if payment.end_date and current_due_date > payment.end_date:
                            logger.info(f"      🔚 Current due date {current_due_date} is beyond end date {payment.end_date}, stopping processing")
                            break
                        
                        # Check if expense already exists for this date
                        existing_expense = Expense.query.filter(
                            Expense.recurring_payment_id == payment.id,
                            Expense.date == current_due_date
                        ).first()
                        
                        if existing_expense:
                            logger.info(f"      ⏭️  Skipped: Expense #{existing_expense.id} already exists for {current_due_date}")
                            skipped_count += 1
                        else:
                            # Create expense for this date
                            logger.info(f"      ✨ Creating expense for {current_due_date}...")
                            
                            try:
                                expense = StartupRecurringProcessor._create_expense_from_recurring_startup(
                                    payment, 
                                    current_due_date
                                )
                                
                                payment_expenses.append(expense)
                                
                                logger.info(f"      ✅ Created expense #{expense.id} for ${expense.amount}")
                                processed_count += 1
                                
                            except Exception as e:
                                logger.error(f"      ❌ Error creating expense for {current_due_date}: {e}")
                                continue
                        
                        # Calculate next occurrence
                        old_due_date = current_due_date
                        current_due_date = payment.calculate_next_due_date(old_due_date)
                        
                        # Safety check to prevent infinite loops
                        if current_due_date <= old_due_date:
                            logger.error(f"      ⚠️  Date calculation error: {old_due_date} -> {current_due_date}")
                            break
                    
                    # FIXED: After processing, check if payment should be deactivated
                    # Calculate what the NEXT due date would be
                    if payment_expenses:  # If we processed any expenses
                        last_processed_date = payment_expenses[-1].date
                        next_would_be_due = payment.calculate_next_due_date(last_processed_date)
                    else:
                        # No expenses processed, use current next_due_date to calculate next
                        next_would_be_due = payment.calculate_next_due_date(payment.next_due_date)
                    
                    # Check if the next due date would be beyond the end date
                    if payment.end_date and next_would_be_due > payment.end_date:
                        # Payment has ended - deactivate it and set sentinel date
                        sentinel_date = datetime(9999, 1, 1)  # Day after end date as sentinel
                        payment.is_active = False
                        payment.next_due_date = sentinel_date  # Set sentinel date
                        payment.last_updated = datetime.utcnow()
                        logger.info(f"      🔚 Next due date {next_would_be_due} would be beyond end date {payment.end_date}")
                        logger.info(f"      🔚 Set payment as inactive with sentinel date: {sentinel_date}")
                    else:
                        # Update the recurring payment's next_due_date to the next future date
                        old_next_due = payment.next_due_date
                        payment.next_due_date = next_would_be_due
                        payment.last_updated = datetime.utcnow()
                        
                        if payment_expenses:
                            logger.info(f"      📅 Updated next due date: {old_next_due} → {payment.next_due_date}")
                
                # Commit all changes
                if processed_count > 0 or skipped_count > 0:
                    db.session.commit()
                    logger.info(f"✅ STARTUP: Processed {processed_count} payments, skipped {skipped_count} (already existed)")
                else:
                    logger.info("ℹ️  STARTUP: No changes made")
                
            except Exception as e:
                logger.error(f"❌ STARTUP ERROR: {e}")
                logger.exception("Full traceback:")
                db.session.rollback()
    
    @staticmethod
    def _create_expense_from_recurring_startup(recurring_payment, expense_date):
        """
        Create an expense record from a recurring payment for startup processing
        FIXED: Only use explicitly defined participants, don't auto-add all users
        """
        from models import ExpenseParticipant, User
        
        # Ensure description has "Recurring" in it
        description = recurring_payment.category_description or ""
        if description.strip() and "recurring" not in description.lower():
            description = f"{description} - Recurring"
        elif not description.strip():
            description = "Recurring"
        
        logger.info(f"      Creating expense with description: '{description}'")
        
        # Create the expense
        expense = Expense(
            amount=recurring_payment.amount,
            category_id=recurring_payment.category_id,
            category_description=description,
            user_id=recurring_payment.user_id,
            date=expense_date,  # Use the specific date passed in
            split_type='equal',
            recurring_payment_id=recurring_payment.id
        )
        
        db.session.add(expense)
        db.session.flush()  # Get the expense ID
        
        logger.info(f"      Added expense to session with ID: {expense.id}")
        
        # FIXED: Only use explicitly defined participants
        participant_ids = recurring_payment.get_participant_ids()
        
        if not participant_ids:
            # FIXED: If no participants specified, only include the payer
            # This prevents auto-adding new users to existing legacy expenses
            participant_ids = [recurring_payment.user_id]
            logger.info(f"      No specific participants, using only payer: {participant_ids}")
        else:
            logger.info(f"      Using explicitly defined participants: {participant_ids}")
        
        # Validate that all participant users still exist
        valid_participants = []
        for user_id in participant_ids:
            user = User.query.get(user_id)
            if user:
                valid_participants.append(user_id)
            else:
                logger.warning(f"      Participant user {user_id} no longer exists, skipping")
        
        if not valid_participants:
            # Fallback to just the payer if no valid participants
            valid_participants = [recurring_payment.user_id]
            logger.info(f"      No valid participants found, using only payer: {valid_participants}")
        
        amount_per_person = recurring_payment.amount / len(valid_participants)
        logger.info(f"      Amount per person: ${amount_per_person:.2f}")
        
        for user_id in valid_participants:
            participant = ExpenseParticipant(
                expense_id=expense.id,
                user_id=user_id,
                amount_owed=amount_per_person
            )
            db.session.add(participant)
            logger.info(f"      Added participant: user {user_id}, owes ${amount_per_person:.2f}")
        
        return expense