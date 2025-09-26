"""
Service for handling recurring payment logic - FIXED with balance updates and proper group filtering
"""
from datetime import datetime, date, timedelta
from app.services.tracker.expense_service import ExpenseService
from models import db, RecurringPayment, Expense, ExpenseParticipant, User, Category
from app.services.tracker.balance_service import BalanceService
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

class RecurringPaymentService:
    
    @staticmethod
    def process_group_due_payments(group_id, check_date=None):
        """
        Process due recurring payments for a specific group
        FIXED: Now properly updates balances and settlements after creating expenses
        """
        if check_date is None:
            check_date = datetime.now().date()
        
        logger.info(f"🔄 PROCESSING: Checking for due/overdue recurring payments for group {group_id} up to {check_date}...")
        
        # Get all active recurring payments for this group that are due or overdue
        due_payments = RecurringPayment.query.filter(
            RecurringPayment.group_id == group_id,
            RecurringPayment.is_active == True,
            RecurringPayment.next_due_date <= check_date
        ).all()
        
        if not due_payments:
            logger.info(f"✅ PROCESSING: No due or overdue recurring payments found for group {group_id}")
            return []
        
        logger.info(f"📋 PROCESSING: Found {len(due_payments)} payments to check for group {group_id}:")
        
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
            
            # Process expenses while respecting end_date
            while current_due_date <= check_date:
                # Check if current_due_date is beyond end_date BEFORE processing
                if recurring_payment.end_date and current_due_date > recurring_payment.end_date:
                    logger.info(f"      🔚 Current due date {current_due_date} is beyond end date {recurring_payment.end_date}, stopping processing")
                    break
                
                # Check if expense already exists for this date
                existing_expense = Expense.query.filter(
                    Expense.recurring_payment_id == recurring_payment.id,
                    Expense.date == current_due_date,
                    Expense.group_id == group_id  # Check group_id too
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
            
            # After processing, check if payment should be deactivated
            if payment_expenses:  # If we processed any expenses
                last_processed_date = payment_expenses[-1].date
                next_would_be_due = recurring_payment.calculate_next_due_date(last_processed_date)
            else:
                # No expenses processed, use current next_due_date to calculate next
                next_would_be_due = recurring_payment.calculate_next_due_date(recurring_payment.next_due_date)
            
            # Check if the next due date would be beyond the end date
            if recurring_payment.end_date and next_would_be_due > recurring_payment.end_date:
                # Payment has ended - deactivate it and set sentinel date
                sentinel_date = datetime(9999, 1, 1)
                recurring_payment.is_active = False
                recurring_payment.next_due_date = sentinel_date
                recurring_payment.last_updated = datetime.utcnow()
                logger.info(f"      🔚 Next due date {next_would_be_due} would be beyond end date {recurring_payment.end_date}")
                logger.info(f"      🔚 Set payment as inactive with sentinel date: {sentinel_date}")
            else:
                # Update the recurring payment's next_due_date to the next future date
                old_next_due = recurring_payment.next_due_date
                recurring_payment.next_due_date = next_would_be_due
                recurring_payment.last_updated = datetime.utcnow()
                
                if payment_expenses:
                    logger.info(f"      📅 Updated next due date: {old_next_due} → {recurring_payment.next_due_date}")
        
        # Commit all changes BEFORE updating balances
        if processed_count > 0 or skipped_count > 0:
            db.session.commit()
            logger.info(f"✅ PROCESSING: Processed {processed_count} payments for group {group_id}, skipped {skipped_count} (already existed)")
            
            # FIXED: Update balances and settlements for the group after creating expenses
            if created_expenses:
                try:
                    logger.info(f"💰 BALANCES: Updating balances for group {group_id} after creating {len(created_expenses)} expenses")
                    BalanceService.recalculate_all_balances()
                    logger.info(f"✅ BALANCES: Successfully updated balances for group {group_id}")
                except Exception as e:
                    logger.error(f"❌ BALANCES: Error updating balances for group {group_id}: {e}")
                    # Don't fail the whole operation if balance update fails
                    
        else:
            logger.info(f"ℹ️  PROCESSING: No changes made for group {group_id}")
        
        return created_expenses
    
    @staticmethod
    def _create_expense_for_date(recurring_payment, expense_date):
        """
        Create an expense record from a recurring payment for a specific date
        FIXED: Properly includes group_id and ensures all required fields
        """
        # Ensure description has "Recurring" in it
        description = recurring_payment.category_description or ""
        if description.strip() and "recurring" not in description.lower():
            description = f"{description} - Recurring"
        elif not description.strip():
            description = "Recurring"
        
        logger.info(f"         Creating expense with description: '{description}' for group {recurring_payment.group_id}")
        
        # FIXED: Ensure group_id is properly set
        if not recurring_payment.group_id:
            raise Exception(f"Recurring payment {recurring_payment.id} has no group_id - cannot create expense")
        
        # Create the expense with proper group_id
        expense = Expense(
            amount=recurring_payment.amount,
            category_id=recurring_payment.category_id,
            category_description=description,
            user_id=recurring_payment.user_id,
            date=expense_date,
            split_type='equal',
            recurring_payment_id=recurring_payment.id,
            group_id=recurring_payment.group_id  # CRITICAL: Include group_id
        )
        
        db.session.add(expense)
        db.session.flush()  # Get the expense ID
        
        logger.info(f"         Added expense to session with ID: {expense.id} for group: {recurring_payment.group_id}")
        
        # Only use explicitly defined participants
        participant_ids = recurring_payment.get_participant_ids()
        
        if not participant_ids:
            # If no participants specified, only include the payer
            participant_ids = [recurring_payment.user_id]
            logger.info(f"         No specific participants, using only payer: {participant_ids}")
        else:
            logger.info(f"         Using explicitly defined participants: {participant_ids}")
        
        # Validate that all participant users still exist and are in the group
        from models import Group
        group = Group.query.get(recurring_payment.group_id)
        if not group:
            raise Exception(f"Group {recurring_payment.group_id} not found")
        
        valid_participants = []
        group_member_ids = [member.id for member in group.members]
        
        for user_id in participant_ids:
            user = User.query.get(user_id)
            if user and user.id in group_member_ids:
                valid_participants.append(user_id)
                logger.info(f"         ✅ Participant user {user_id} ({user.name}) is valid group member")
            else:
                logger.warning(f"         ⚠️  Participant user {user_id} no longer exists or not in group, skipping")
        
        if not valid_participants:
            # Fallback to just the payer if no valid participants
            if recurring_payment.user_id in group_member_ids:
                valid_participants = [recurring_payment.user_id]
                logger.info(f"         Using only payer as fallback: {valid_participants}")
            else:
                raise Exception(f"Payer user {recurring_payment.user_id} is not in group {recurring_payment.group_id}")
        
        amount_per_person = recurring_payment.amount / len(valid_participants)
        logger.info(f"         Amount per person: ${amount_per_person:.2f} (split among {len(valid_participants)} participants)")
        
        for user_id in valid_participants:
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
        """
        Legacy method - now uses unified logic
        FIXED: Also updates balances after manual processing
        """
        expense = RecurringPaymentService._create_expense_for_date(recurring_payment, expense_date)
        
        # Update balances after manual processing
        try:
            db.session.commit()  # Commit the expense first
            logger.info(f"💰 MANUAL: Updating balances for group {recurring_payment.group_id} after manual processing")
            BalanceService.recalculate_all_balances()
            logger.info(f"✅ MANUAL: Successfully updated balances for group {recurring_payment.group_id}")
        except Exception as e:
            logger.error(f"❌ MANUAL: Error updating balances: {e}")
            # Don't fail the operation, but log the error
            
        return expense
    
    @staticmethod
    def create_recurring_payment(data):
        """
        Create a new recurring payment - WITH GROUP CONTEXT
        FIXED: Better group validation and balance updates
        """
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        current_date = datetime.now().date()
        group_id = int(data.get('group_id'))
        
        if not group_id:
            raise ValueError("Group ID is required")
        
        # Validate group exists
        from models import Group
        group = Group.query.get(group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")
        
        logger.info(f"[CREATE] Start date: {start_date}, Current date: {current_date}, Group: {group_id}")
        
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
            is_active=True,
            group_id=group_id  # Set group_id
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
            
            # Use the same unified logic to create all past expenses (includes balance updates)
            created_expenses = RecurringPaymentService.process_group_due_payments(group_id, current_date)
            logger.info(f"[CREATE] Created {len(created_expenses)} past expenses with balance updates")
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
                new_end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
                recurring_payment.end_date = new_end_date
                
                # If updating end_date, check if payment should now be inactive
                if recurring_payment.next_due_date and recurring_payment.next_due_date > new_end_date:
                    sentinel_date = datetime(9999, 1, 1)
                    recurring_payment.is_active = False
                    recurring_payment.next_due_date = sentinel_date
                    logger.info(f"[UPDATE] End date {new_end_date} is before next due date, set inactive with sentinel {sentinel_date}")
            else:
                recurring_payment.end_date = None
        
        if 'is_active' in data:
            if isinstance(data['is_active'], bool):
                recurring_payment.is_active = data['is_active']
            else:
                recurring_payment.is_active = str(data['is_active']).lower() == 'true'
        
        if 'next_due_date' in data and data['next_due_date']:
            new_next_due = datetime.strptime(data['next_due_date'], '%Y-%m-%d').date()
            recurring_payment.next_due_date = new_next_due
            
            # If updating next_due_date, check if it's beyond end_date
            if recurring_payment.end_date and new_next_due > recurring_payment.end_date:
                sentinel_date = datetime(9999, 1, 1)
                recurring_payment.is_active = False
                recurring_payment.next_due_date = sentinel_date
                logger.info(f"[UPDATE] Next due date {new_next_due} is beyond end date {recurring_payment.end_date}, set inactive with sentinel {sentinel_date}")
        
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
    def get_all_recurring_payments(group_id=None, only_active=True):
        """Get all recurring payments, optionally filtered by group and active status"""
        query = RecurringPayment.query

        if group_id is not None:
            query = query.filter_by(group_id=group_id)

        if only_active:
            query = query.filter_by(is_active=True)

        return query.all()
    
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
    
    @staticmethod
    def process_due_payments(check_date=None):
        """
        Process due payments for ALL groups (for system-wide processing)
        FIXED: Ensures all groups get their balances updated
        """
        if check_date is None:
            check_date = datetime.now().date()
        
        from models import Group
        all_groups = Group.query.all()
        
        all_created_expenses = []
        groups_with_updates = []
        
        for group in all_groups:
            logger.info(f"🏢 Processing recurring payments for group {group.id} ({group.name})")
            group_expenses = RecurringPaymentService.process_group_due_payments(group.id, check_date)
            all_created_expenses.extend(group_expenses)
            
            if group_expenses:
                groups_with_updates.append(group.id)
        
        logger.info(f"✅ SYSTEM-WIDE: Processed {len(all_created_expenses)} expenses across {len(groups_with_updates)} groups")
        
        return all_created_expenses