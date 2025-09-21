# Fixed startup_processor.py - Replace the balance update section

"""
Startup processor for recurring payments - FIXED with correct balance service call
"""

import logging
from datetime import datetime, date, timedelta
from models import db, RecurringPayment, Expense, Group

# FIXED: Import the correct service for balance calculation
from app.services.expense_service import ExpenseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StartupRecurringProcessor:
    """Process missed and due recurring payments on app startup"""
    
    @staticmethod
    def process_startup_recurring_payments(app):
        """
        Process any recurring payments that are due or overdue on app startup
        FIXED: Now processes by group and calls correct balance service
        """
        with app.app_context():
            try:
                logger.info("🚀 STARTUP: Checking for due/overdue recurring payments...")
                
                today = date.today()
                
                # CRITICAL FIX: Process by group to maintain group context
                all_groups = Group.query.all()
                
                if not all_groups:
                    logger.info("ℹ️  STARTUP: No groups found")
                    return
                
                logger.info(f"🏢 STARTUP: Found {len(all_groups)} groups to check")
                
                total_processed = 0
                total_skipped = 0
                groups_with_updates = []
                
                for group in all_groups:
                    logger.info(f"📋 STARTUP: Checking group {group.id} ({group.name})")
                    
                    # Get due payments for this specific group
                    due_and_overdue = RecurringPayment.query.filter(
                        RecurringPayment.group_id == group.id,
                        RecurringPayment.is_active == True,
                        RecurringPayment.next_due_date <= today
                    ).all()
                    
                    if not due_and_overdue:
                        logger.info(f"   ✅ No due payments for group {group.id}")
                        continue
                    
                    logger.info(f"   📋 Found {len(due_and_overdue)} payments to check:")
                    
                    group_processed = 0
                    group_skipped = 0
                    
                    for payment in due_and_overdue:
                        # CRITICAL: Verify payment belongs to this group
                        if payment.group_id != group.id:
                            logger.error(f"   ❌ CRITICAL: Payment {payment.id} has group_id {payment.group_id} but processing group {group.id}")
                            continue
                        
                        days_diff = (today - payment.next_due_date).days
                        status = "due today" if days_diff == 0 else f"overdue by {days_diff} days"
                        
                        logger.info(f"   🔍 Checking: {payment.category_obj.name} - ${payment.amount} ({status})")
                        
                        # Process ALL missed dates from next_due_date up through today
                        current_due_date = payment.next_due_date
                        payment_expenses = []
                        
                        while current_due_date <= today:
                            # Check if current_due_date is beyond end_date BEFORE processing
                            if payment.end_date and current_due_date > payment.end_date:
                                logger.info(f"      🔚 Current due date {current_due_date} is beyond end date {payment.end_date}, stopping processing")
                                break
                            
                            # CRITICAL: Check for existing expense with GROUP_ID filter
                            existing_expense = Expense.query.filter(
                                Expense.recurring_payment_id == payment.id,
                                Expense.date == current_due_date,
                                Expense.group_id == group.id  # CRITICAL: Add group_id filter
                            ).first()
                            
                            if existing_expense:
                                logger.info(f"      ⏭️  Skipped: Expense #{existing_expense.id} already exists for {current_due_date}")
                                group_skipped += 1
                            else:
                                # Create expense for this date with GROUP CONTEXT
                                logger.info(f"      ✨ Creating expense for {current_due_date}...")
                                
                                try:
                                    expense = StartupRecurringProcessor._create_expense_from_recurring_startup(
                                        payment, 
                                        current_due_date,
                                        group  # CRITICAL: Pass group context
                                    )
                                    
                                    payment_expenses.append(expense)
                                    
                                    logger.info(f"      ✅ Created expense #{expense.id} for ${expense.amount}")
                                    group_processed += 1
                                    
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
                        
                        # Update recurring payment next_due_date
                        if payment_expenses:  # If we processed any expenses
                            last_processed_date = payment_expenses[-1].date
                            next_would_be_due = payment.calculate_next_due_date(last_processed_date)
                        else:
                            next_would_be_due = payment.calculate_next_due_date(payment.next_due_date)
                        
                        # Check if the next due date would be beyond the end date
                        if payment.end_date and next_would_be_due > payment.end_date:
                            # Payment has ended - deactivate it and set sentinel date
                            sentinel_date = datetime(9999, 1, 1)
                            payment.is_active = False
                            payment.next_due_date = sentinel_date
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
                    
                    # Track groups that had updates
                    if group_processed > 0:
                        groups_with_updates.append(group.id)
                    
                    total_processed += group_processed
                    total_skipped += group_skipped
                    
                    if group_processed > 0 or group_skipped > 0:
                        logger.info(f"   📊 Group {group.id}: processed {group_processed}, skipped {group_skipped}")
                
                # Commit all changes
                if total_processed > 0 or total_skipped > 0:
                    db.session.commit()
                    logger.info(f"✅ STARTUP: Processed {total_processed} payments, skipped {total_skipped} (already existed)")
                    
                    # FIXED: Use the correct method to update balances
                    if groups_with_updates:
                        logger.info(f"💰 STARTUP: Updating balances for {len(groups_with_updates)} groups...")
                        
                        for group_id in groups_with_updates:
                            try:
                                # FIXED: Use ExpenseService._recalculate_group_balances instead
                                ExpenseService._recalculate_group_balances(group_id)
                                group = Group.query.get(group_id)
                                group_name = group.name if group else f"Group {group_id}"
                                logger.info(f"   ✅ Updated balances for {group_name}")
                            except Exception as e:
                                logger.error(f"   ❌ Error updating balances for group {group_id}: {e}")
                        
                        logger.info("🎉 STARTUP: Balance updates completed")
                else:
                    logger.info("ℹ️  STARTUP: No changes made")
                
            except Exception as e:
                logger.error(f"❌ STARTUP ERROR: {e}")
                logger.exception("Full traceback:")
                db.session.rollback()
    
    @staticmethod
    def _create_expense_from_recurring_startup(recurring_payment, expense_date, group):
        """
        Create an expense record from a recurring payment for startup processing
        CRITICAL FIX: Now includes group_id and validates group membership
        """
        from models import ExpenseParticipant, User
        
        # CRITICAL: Validate group_id exists
        if not recurring_payment.group_id:
            error_msg = f"CRITICAL: Recurring payment {recurring_payment.id} has no group_id"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        if recurring_payment.group_id != group.id:
            error_msg = f"CRITICAL: Group mismatch - payment has group_id {recurring_payment.group_id}, processing group {group.id}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Ensure description has "Recurring" in it
        description = recurring_payment.category_description or ""
        if description.strip() and "recurring" not in description.lower():
            description = f"{description} - Recurring"
        elif not description.strip():
            description = "Recurring"
        
        logger.info(f"         Creating expense with description: '{description}' for group {group.id}")
        
        # CRITICAL FIX: Create the expense WITH group_id
        expense = Expense(
            amount=recurring_payment.amount,
            category_id=recurring_payment.category_id,
            category_description=description,
            user_id=recurring_payment.user_id,
            date=expense_date,
            split_type='equal',
            recurring_payment_id=recurring_payment.id,
            group_id=recurring_payment.group_id  # CRITICAL: This was missing!
        )
        
        # Validate the group_id was set correctly
        if expense.group_id != recurring_payment.group_id:
            error_msg = f"CRITICAL: Expense group_id {expense.group_id} doesn't match recurring payment group_id {recurring_payment.group_id}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        db.session.add(expense)
        db.session.flush()  # Get the expense ID
        
        logger.info(f"         Added expense to session with ID: {expense.id} for group: {expense.group_id}")
        
        # Get participants and validate they're group members
        participant_ids = recurring_payment.get_participant_ids()
        
        if not participant_ids:
            participant_ids = [recurring_payment.user_id]
            logger.info(f"         No specific participants, using only payer: {participant_ids}")
        else:
            logger.info(f"         Using explicitly defined participants: {participant_ids}")
        
        # CRITICAL: Validate participants are still group members
        group_member_ids = [member.id for member in group.members]
        valid_participants = []
        
        for user_id in participant_ids:
            user = User.query.get(user_id)
            if user and user_id in group_member_ids:
                valid_participants.append(user_id)
                logger.info(f"         ✅ Participant {user.name} (ID: {user_id}) is valid group member")
            else:
                logger.warning(f"         ⚠️  Participant user {user_id} no longer exists or not in group, skipping")
        
        if not valid_participants:
            # Fallback to just the payer if they're in the group
            if recurring_payment.user_id in group_member_ids:
                valid_participants = [recurring_payment.user_id]
                logger.info(f"         Using only payer as fallback: {valid_participants}")
            else:
                error_msg = f"CRITICAL: No valid participants including payer {recurring_payment.user_id} for group {group.id}"
                logger.error(error_msg)
                raise Exception(error_msg)
        
        amount_per_person = recurring_payment.amount / len(valid_participants)
        logger.info(f"         Amount per person: ${amount_per_person:.2f} ({len(valid_participants)} participants)")
        
        for user_id in valid_participants:
            participant = ExpenseParticipant(
                expense_id=expense.id,
                user_id=user_id,
                amount_owed=amount_per_person
            )
            db.session.add(participant)
            logger.info(f"         Added participant: user {user_id}, owes ${amount_per_person:.2f}")
        
        # Final validation
        logger.info(f"         ✅ CREATED: Expense {expense.id}, amount=${expense.amount}, group={expense.group_id}, participants={len(valid_participants)}")
        
        return expense