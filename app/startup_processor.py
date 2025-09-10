"""
Startup processor for recurring payments - UPDATED WITH END DATE LOGIC
Now matches the unified logic from recurring_service.py
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
        UNIFIED: Now uses the same comprehensive logic as the service
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
                    
                    # Determine the actual end date for processing
                    effective_end_date = today
                    if payment.end_date and payment.end_date < today:
                        effective_end_date = payment.end_date
                        logger.info(f"      📅 Payment has end_date {payment.end_date}, limiting processing to that date")
                    
                    while current_due_date <= effective_end_date:
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
                    
                    # After processing all valid dates, check if payment should be deactivated
                    if payment.end_date and current_due_date > payment.end_date:
                        # Payment has ended - deactivate it and clear next_due_date
                        payment.is_active = False
                        payment.next_due_date = None  # Set to NULL to indicate completion
                        payment.last_updated = datetime.utcnow()
                        logger.info(f"      🔚 Payment ended on {payment.end_date}, marked as inactive with next_due_date cleared")
                    else:
                        # Update the recurring payment's next_due_date to the next future date
                        old_next_due = payment.next_due_date
                        payment.next_due_date = current_due_date
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
        UNIFIED: Now matches the service method exactly
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
        
        # Add participants
        participant_ids = recurring_payment.get_participant_ids()
        if not participant_ids:
            # If no participants specified, use all users
            participant_ids = [user.id for user in User.query.all()]
            logger.info(f"      No specific participants, using all users: {participant_ids}")
        else:
            logger.info(f"      Using specified participants: {participant_ids}")
        
        amount_per_person = recurring_payment.amount / len(participant_ids)
        logger.info(f"      Amount per person: ${amount_per_person:.2f}")
        
        for user_id in participant_ids:
            participant = ExpenseParticipant(
                expense_id=expense.id,
                user_id=user_id,
                amount_owed=amount_per_person
            )
            db.session.add(participant)
            logger.info(f"      Added participant: user {user_id}, owes ${amount_per_person:.2f}")
        
        return expense