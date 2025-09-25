# app/services/auth/account_deletion_service.py - FIXED version

from models import db, User, Group, Balance, Expense, ExpenseParticipant, Settlement, RecurringPayment, Category, user_groups
from flask import current_app
from sqlalchemy import func, and_
from datetime import datetime
import secrets
import string

class AccountDeletionService:
    """Handle secure account deletion with data preservation for shared groups"""
    
    @staticmethod
    def check_deletion_eligibility(user):
        """
        Check if user can delete their account and what the implications are
        
        Returns:
            dict: {
                'can_delete': bool,
                'warnings': [list of warning messages],
                'blocking_issues': [list of issues that prevent deletion],
                'shared_groups': [groups where user will be replaced with placeholder],
                'personal_groups': [groups that will be deleted],
                'admin_groups': [groups where user is admin and needs to transfer rights]
            }
        """
        warnings = []
        blocking_issues = []
        shared_groups = []
        personal_groups = []
        admin_groups = []
        
        # Get all groups user belongs to
        user_groups_list = user.groups
        
        for group in user_groups_list:
            member_count = group.get_member_count()
            
            if member_count == 1:
                # Personal tracker - will be deleted
                personal_groups.append({
                    'id': group.id,
                    'name': group.name,
                    'expense_count': len(group.expenses)
                })
            else:
                # Shared group - user will be replaced with placeholder
                shared_groups.append({
                    'id': group.id,
                    'name': group.name,
                    'member_count': member_count,
                    'expense_count': len([e for e in group.expenses if e.user_id == user.id]),
                    'balance': user.get_group_balance(group.id)
                })
                
                # Check if user is admin
                if user.is_group_admin(group) or group.creator_id == user.id:
                    admin_groups.append({
                        'id': group.id,
                        'name': group.name,
                        'member_count': member_count
                    })
        
        # Check for admin groups that would block deletion
        if admin_groups:
            for group_info in admin_groups:
                blocking_issues.append(
                    f"You are an admin of '{group_info['name']}' with {group_info['member_count']} members. "
                    f"Transfer admin rights to another member before deleting your account."
                )
        
        # Add warnings for shared groups with balances
        for group_info in shared_groups:
            if abs(group_info['balance']) > 0.01:
                if group_info['balance'] > 0:
                    warnings.append(
                        f"In '{group_info['name']}', you are owed ${group_info['balance']:.2f}. "
                        f"This balance will be preserved with a placeholder account."
                    )
                else:
                    warnings.append(
                        f"In '{group_info['name']}', you owe ${abs(group_info['balance']):.2f}. "
                        f"This balance will be preserved with a placeholder account."
                    )
        
        # Add warnings for expenses that will be preserved
        total_shared_expenses = sum(g['expense_count'] for g in shared_groups)
        if total_shared_expenses > 0:
            warnings.append(
                f"Your {total_shared_expenses} expense(s) in shared groups will be preserved "
                f"with a placeholder account to maintain group history."
            )
        
        # Add warnings for personal data deletion
        total_personal_expenses = sum(g['expense_count'] for g in personal_groups)
        if total_personal_expenses > 0:
            warnings.append(
                f"Your {len(personal_groups)} personal tracker(s) and {total_personal_expenses} "
                f"personal expense(s) will be permanently deleted."
            )
        
        can_delete = len(blocking_issues) == 0
        
        return {
            'can_delete': can_delete,
            'warnings': warnings,
            'blocking_issues': blocking_issues,
            'shared_groups': shared_groups,
            'personal_groups': personal_groups,
            'admin_groups': admin_groups
        }
    
    @staticmethod
    def create_placeholder_user(original_user):
        """
        Create a placeholder user to replace the deleted user in shared groups
        
        Returns:
            User: The placeholder user object
        """
        # Generate a unique placeholder email
        placeholder_id = ''.join(secrets.choice(string.digits) for _ in range(8))
        placeholder_email = f"deleted-user-{placeholder_id}@placeholder.local"
        
        # Create placeholder user
        placeholder = User(
            full_name=f"[Deleted User] {original_user.display_name}",
            display_name=f"{original_user.display_name} (Deleted)",  # Keep same display name for recognition
            email=placeholder_email,
            is_active=False,  # Cannot login
            created_at=datetime.utcnow(),
            # No password hash - cannot login
        )
        
        db.session.add(placeholder)
        db.session.flush()  # Get the ID
        
        current_app.logger.info(f"Created placeholder user {placeholder.id} for {original_user.display_name}")
        return placeholder
    
    # In account_deletion_service.py

    # In account_deletion_service.py

    # In account_deletion_service.py

    @staticmethod
    def transfer_user_data_to_placeholder(original_user, placeholder_user, shared_group_ids):
        """
        Transfer user data to placeholder for shared groups only using bulk updates.
        This version uses a subquery to correctly update expense participants.
        """
        if not shared_group_ids:
            return

        original_user_id = original_user.id
        placeholder_user_id = placeholder_user.id

        # --- Use direct UPDATE statements to avoid ORM session confusion ---

        # Transfer Expenses created by the user
        expenses_updated = Expense.query.filter(
            Expense.user_id == original_user_id,
            Expense.group_id.in_(shared_group_ids)
        ).update({'user_id': placeholder_user_id}, synchronize_session=False)

        # --- THIS IS THE CORRECTED QUERY USING A SUBQUERY ---
        # 1. Create a subquery to find all expense IDs within the shared groups.
        expense_ids_in_shared_groups = db.session.query(Expense.id).filter(
            Expense.group_id.in_(shared_group_ids)
        ).scalar_subquery()

        # 2. Update the participants whose expense_id is in that subquery.
        participations_updated = ExpenseParticipant.query.filter(
            ExpenseParticipant.user_id == original_user_id,
            ExpenseParticipant.expense_id.in_(expense_ids_in_shared_groups)
        ).update({'user_id': placeholder_user_id}, synchronize_session=False)
        # ----------------------------------------------------

        # Transfer Balances
        balances_updated = Balance.query.filter(
            Balance.user_id == original_user_id,
            Balance.group_id.in_(shared_group_ids)
        ).update({'user_id': placeholder_user_id}, synchronize_session=False)

        # Transfer Settlements (where the user was the payer)
        settlements_made_updated = Settlement.query.filter(
            Settlement.payer_id == original_user_id,
            Settlement.group_id.in_(shared_group_ids)
        ).update({'payer_id': placeholder_user_id}, synchronize_session=False)

        # Transfer Settlements (where the user was the receiver)
        settlements_received_updated = Settlement.query.filter(
            Settlement.receiver_id == original_user_id,
            Settlement.group_id.in_(shared_group_ids)
        ).update({'receiver_id': placeholder_user_id}, synchronize_session=False)

        settlements_updated = settlements_made_updated + settlements_received_updated

        # Transfer Recurring Payments
        recurring_updated = RecurringPayment.query.filter(
            RecurringPayment.user_id == original_user_id,
            RecurringPayment.group_id.in_(shared_group_ids)
        ).update({'user_id': placeholder_user_id}, synchronize_session=False)

        current_app.logger.info(
            f"Transferred data to placeholder: {expenses_updated} expenses, "
            f"{participations_updated} participations, {balances_updated} balances, "
            f"{settlements_updated} settlements, {recurring_updated} recurring payments"
        )
    
    # app/services/auth/account_deletion_service.py

    @staticmethod
    def update_group_memberships(original_user, placeholder_user, shared_group_ids):
        """
        Update group memberships - replace user with placeholder in shared groups only
        (ORM-compliant version)
        """
        for group_id in shared_group_ids:
            # Fetch the actual Group object
            group = Group.query.get(group_id)
            if group:
                # Let the ORM handle the association table by modifying the relationship
                if original_user in group.members:
                    group.members.remove(original_user)
                
                # Add the placeholder
                group.members.append(placeholder_user)
                
                current_app.logger.info(f"Replaced user in group {group_id} with placeholder")
    
    # app/services/auth/account_deletion_service.py

    @staticmethod
    def delete_personal_groups_and_associations(group_ids, user_id):
        """
        Delete personal groups. The cascade deletes the associations.
        (ORM-compliant version)
        """
        for group_id in group_ids:
            group = Group.query.get(group_id)
            # We only delete the group if it's truly a personal group (member count <= 1)
            if group and group.get_member_count() <= 1:
                current_app.logger.info(f"Deleting personal group: {group.name}")
                
                # The ORM, thanks to the cascade setting in models.py, will
                # automatically delete the association from the user_groups table
                # before deleting the group itself. No manual delete is needed.
                db.session.delete(group)
                    
    
    # app/services/auth/account_deletion_service.py

    @staticmethod
    def delete_user_account(user):
        """
        Perform the complete account deletion process
        """
        try:
            # Check eligibility first
            eligibility = AccountDeletionService.check_deletion_eligibility(user)
            if not eligibility['can_delete']:
                return False, "Cannot delete account: " + "; ".join(eligibility['blocking_issues'])
            
            original_display_name = user.display_name
            user_id = user.id
            shared_group_ids = [g['id'] for g in eligibility['shared_groups']]
            personal_group_ids = [g['id'] for g in eligibility['personal_groups']]
            
            placeholder_user = None
            
            # Step 1: Handle shared groups (This part is correct and remains the same)
            if shared_group_ids:
                placeholder_user = AccountDeletionService.create_placeholder_user(user)
                AccountDeletionService.transfer_user_data_to_placeholder(
                    user, placeholder_user, shared_group_ids
                )
                AccountDeletionService.update_group_memberships(
                    user, placeholder_user, shared_group_ids
                )
            
            # --- REVISED Step 2: Explicitly delete all data within personal trackers ---
            if personal_group_ids:
                current_app.logger.info(f"Deleting data from {len(personal_group_ids)} personal tracker(s).")

                # Fetch the actual Group objects to be deleted
                personal_groups_to_delete = Group.query.filter(Group.id.in_(personal_group_ids)).all()

                for group in personal_groups_to_delete:
                    # *** THIS IS THE CRITICAL FIX ***
                    # Manually remove the group from the user's collection in the session.
                    # This tells the ORM that the link is severed, preventing it from
                    # trying to delete the user_groups entry later.
                    if group in user.groups:
                        user.groups.remove(group)

                # Now that the session is in sync, proceed with efficient bulk deletes.
                # We are deleting the contents before the groups.
                ExpenseParticipant.query.filter(ExpenseParticipant.group_id.in_(personal_group_ids)).delete(synchronize_session=False)
                Expense.query.filter(Expense.group_id.in_(personal_group_ids)).delete(synchronize_session=False)
                RecurringPayment.query.filter(RecurringPayment.group_id.in_(personal_group_ids)).delete(synchronize_session=False)
                Balance.query.filter(Balance.group_id.in_(personal_group_ids)).delete(synchronize_session=False)
                Settlement.query.filter(Settlement.group_id.in_(personal_group_ids)).delete(synchronize_session=False)
                Category.query.filter(Category.group_id.in_(personal_group_ids)).delete(synchronize_session=False)

                # Finally, delete the group objects themselves.
                # The ON DELETE CASCADE in your database will handle the user_groups table.
                Group.query.filter(Group.id.in_(personal_group_ids)).delete(synchronize_session=False)

            # Step 3: Delete any remaining personal data that is NOT in a group (if any)
            Category.query.filter_by(user_id=user_id, group_id=None).delete(synchronize_session=False)

            # Step 4: Delete the user account
            # The session now correctly knows the user has no more group memberships,
            # so this will succeed without conflict.
            db.session.delete(user)

            # Commit all changes
            db.session.commit()
            
            shared_count = len(shared_group_ids)
            personal_count = len(personal_group_ids)
            
            message_parts = []
            message_parts.append(f"Account for '{original_display_name}' has been deleted.")
            
            if shared_count > 0:
                message_parts.append(
                    f"Your data in {shared_count} shared group(s) has been preserved "
                    f"with a placeholder account to maintain group history."
                )
            
            if personal_count > 0:
                message_parts.append(
                    f"{personal_count} personal tracker(s) and all associated data have been permanently deleted."
                )
            
            success_message = " ".join(message_parts)
            
            current_app.logger.info(f"Successfully deleted account: {original_display_name}")
            return True, success_message
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting account: {str(e)}"
            current_app.logger.error(error_msg)
            return False, error_msg