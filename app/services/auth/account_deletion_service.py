# app/services/auth/account_deletion_service.py - Handle account deletion with placeholder logic

from models import db, User, Group, Balance, Expense, ExpenseParticipant, Settlement, RecurringPayment, Category, user_groups
from flask import current_app
from sqlalchemy import func
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
            display_name=original_user.display_name,  # Keep same display name for recognition
            email=placeholder_email,
            is_active=False,  # Cannot login
            created_at=datetime.utcnow(),
            # No password hash - cannot login
        )
        
        db.session.add(placeholder)
        db.session.flush()  # Get the ID
        
        current_app.logger.info(f"Created placeholder user {placeholder.id} for {original_user.display_name}")
        return placeholder
    
    @staticmethod
    def transfer_user_data_to_placeholder(original_user, placeholder_user, shared_group_ids):
        """
        Transfer user data to placeholder for shared groups only
        
        Args:
            original_user: The user being deleted
            placeholder_user: The placeholder user
            shared_group_ids: List of group IDs where data should be transferred
        """
        # Transfer expenses in shared groups
        expenses_updated = 0
        for expense in original_user.expenses:
            if expense.group_id in shared_group_ids:
                expense.user_id = placeholder_user.id
                expenses_updated += 1
        
        # Transfer expense participations in shared groups
        participations_updated = 0
        for participation in original_user.expense_participants:
            if participation.group_id in shared_group_ids:
                participation.user_id = placeholder_user.id
                participations_updated += 1
        
        # Transfer balances for shared groups
        balances_updated = 0
        for balance in original_user.balances:
            if balance.group_id in shared_group_ids:
                balance.user_id = placeholder_user.id
                balance.last_updated = datetime.utcnow()
                balances_updated += 1
        
        # Transfer settlements in shared groups
        settlements_updated = 0
        for settlement in original_user.settlements_made:
            if settlement.group_id in shared_group_ids:
                settlement.payer_id = placeholder_user.id
                settlements_updated += 1
        
        for settlement in original_user.settlements_received:
            if settlement.group_id in shared_group_ids:
                settlement.receiver_id = placeholder_user.id
                settlements_updated += 1
        
        # Transfer recurring payments in shared groups
        recurring_updated = 0
        for recurring in original_user.recurring_payments:
            if recurring.group_id in shared_group_ids:
                recurring.user_id = placeholder_user.id
                recurring_updated += 1
        
        current_app.logger.info(
            f"Transferred data to placeholder: {expenses_updated} expenses, "
            f"{participations_updated} participations, {balances_updated} balances, "
            f"{settlements_updated} settlements, {recurring_updated} recurring payments"
        )
    
    @staticmethod
    def update_group_memberships(original_user, placeholder_user, shared_group_ids):
        """
        Update group memberships - replace user with placeholder in shared groups only
        Personal groups are handled separately and don't need membership updates
        """
        # Replace user with placeholder in shared groups only
        for group_id in shared_group_ids:
            # Get the user's role in the group (if it still exists)
            association = db.session.query(user_groups).filter_by(
                user_id=original_user.id,
                group_id=group_id
            ).first()

            if association:
                user_role = association.role
                joined_at = association.joined_at

                
                # Remove original user from group
                db.session.execute(
                    user_groups.delete()
                    .where(user_groups.c.user_id == original_user.id,
                        user_groups.c.group_id == group_id)
                    .execution_options(synchronize_session=False)   # <---- here too
                )
                
                # Add placeholder user to group
                db.session.execute(
                    user_groups.insert().values(
                        user_id=placeholder_user.id,
                        group_id=group_id,
                        role=user_role,
                        joined_at=joined_at
                    )
                )
                
                current_app.logger.info(f"Replaced user in group {group_id} with placeholder")
    
    @staticmethod
    def delete_personal_groups(group_ids, user_id):
        """
        Delete personal groups entirely (groups with only one member)
        But preserve user associations with other groups
        
        Args:
            group_ids: List of group IDs to delete
            user_id: ID of the user being deleted
        """
        for group_id in group_ids:
            group = Group.query.get(group_id)
            if group and group.get_member_count() <= 1:
                # Manually remove the user from this specific group first
                db.session.execute(
                    user_groups.delete().where(
                        user_groups.c.user_id == user_id,
                        user_groups.c.group_id == group_id
                    )
                )
                # Then delete the group
                db.session.delete(group)
                current_app.logger.info(f"Deleted personal group: {group.name}")
    
    @staticmethod
    def delete_user_account(user):
        """
        Perform the complete account deletion process
        
        Args:
            user: The user to delete
        
        Returns:
            tuple: (success_bool, message_string)
        """
        try:
            # Check eligibility first
            eligibility = AccountDeletionService.check_deletion_eligibility(user)
            if not eligibility['can_delete']:
                return False, "Cannot delete account: " + "; ".join(eligibility['blocking_issues'])
            
            original_display_name = user.display_name
            shared_group_ids = [g['id'] for g in eligibility['shared_groups']]
            personal_group_ids = [g['id'] for g in eligibility['personal_groups']]
            
            placeholder_user = None
            
            # Create placeholder user if there are shared groups
            if shared_group_ids:
                placeholder_user = AccountDeletionService.create_placeholder_user(user)
                
                # Transfer data to placeholder for shared groups
                AccountDeletionService.transfer_user_data_to_placeholder(
                    user, placeholder_user, shared_group_ids
                )
                
                # Update group memberships for shared groups first
                AccountDeletionService.update_group_memberships(
                    user, placeholder_user, shared_group_ids
                )
            
            # Delete personal groups (this will handle their user associations)
            if personal_group_ids:
                AccountDeletionService.delete_personal_groups(personal_group_ids, user.id)
            
            # Delete any remaining personal data
            # Categories that are user-specific (not group-specific)
            personal_categories = Category.query.filter_by(user_id=user.id, group_id=None).all()
            for category in personal_categories:
                db.session.delete(category)
            
            # Clean up any remaining user-group associations
            # (should only be any leftover ones at this point)
            # Cleanup any remaining user-group associations
            remaining_associations = db.session.execute(
                user_groups.select().where(user_groups.c.user_id == user.id)
            ).fetchall()

            if remaining_associations:
                current_app.logger.info(
                    f"Cleaning up {len(remaining_associations)} remaining group associations for user {user.id}"
                )

            db.session.execute(
                user_groups.delete()
                .where(user_groups.c.user_id == user.id)
                .execution_options(synchronize_session=False)   # <---- make delete idempotent
            )

            # Delete the original user account
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