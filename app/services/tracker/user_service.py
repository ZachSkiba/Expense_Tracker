from models import db, User, Expense, Balance, ExpenseParticipant, Group
from flask import url_for
from sqlalchemy import func

class UserService:
    
    @staticmethod
    def get_all():
        """Get all users"""
        return User.query.all()
    
    @staticmethod
    def get_all_data():
        """Get all users as list of dicts for JSON/template use"""
        users = User.query.all()
        return [{'id': u.id, 'name': u.name} for u in users]
    
    @staticmethod
    def create_user(name, group_id=None):
        """
        Create a new user and optionally add to a group
        
        Returns:
            tuple: (user_object, error_message)
        """
        name = name.strip()
        if not name:
            return None, "Name cannot be empty"
        
        # Check if user already exists
        existing_user = User.query.filter_by(name=name).first()
        if existing_user:
            if group_id:
                group = Group.query.get(group_id)
                if group and existing_user not in group.members:
                    # User exists but not in group - add them
                    try:
                        group.add_member(existing_user)
                        db.session.commit()
                        return existing_user, None
                    except Exception as e:
                        db.session.rollback()
                        return None, str(e)
                else:
                    return None, f"User '{name}' is already in this group"
            else:
                return None, f"User '{name}' already exists"
        
        try:
            new_user = User(name=name)
            db.session.add(new_user)
            db.session.flush()  # Get the user ID
            
            # Add to group if specified
            if group_id:
                group = Group.query.get(group_id)
                if group:
                    group.add_member(new_user)
            
            db.session.commit()
            return new_user, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def can_delete_user(user_id, group_id=None):
        """
        Check if user can be safely deleted or removed from group
        Only checks for non-zero balances - historical activity doesn't prevent removal if balance is settled
        
        Args:
            user_id: ID of user to check
            group_id: If provided, check constraints within this group only
        
        Returns:
            tuple: (can_delete_boolean, list_of_reason_strings)
        """
        user = User.query.get_or_404(user_id)
        reasons = []
        
        if group_id:
            # Group-specific checks
            group = Group.query.get(group_id)
            if not group:
                return False, ["Group not found"]
            
            if user.id == group.creator_id:  # Fixed: use user.id and creator_id
                return False, ["Cannot remove the group creator"]
            
            # ONLY check if user has non-zero balance in this group
            # Historical expenses/settlements don't matter if balance is settled
            balance = Balance.query.filter_by(user_id=user_id, group_id=group_id).first()
            if balance and abs(balance.amount) > 0.01:
                balance_url = url_for('expenses.group_tracker', group_id=group_id)
                if balance.amount > 0:
                    reasons.append(
                        f"{user.name} is owed <strong>${balance.amount:.2f}</strong> "
                        f"(<a href='{balance_url}'>settle balance first</a>)"
                    )
                else:
                    reasons.append(
                        f"{user.name} owes <strong>${abs(balance.amount):.2f}</strong> "
                        f"(<a href='{balance_url}'>settle balance first</a>)"
                    )
            
            # If balance is zero or doesn't exist, user can be removed regardless of historical activity
            # No other checks needed for group-specific removal
            
        else:
            # Global checks (legacy method for full user deletion)
            # For global deletion, we still check expenses since it affects other users
            payer_expenses = user.expenses
            if payer_expenses:
                expense_url = url_for('dashboard.home')
                reasons.append(
                    f"{user.name} paid for "
                    f"<a href='{expense_url}'>{len(payer_expenses)} expense(s)</a>"
                )
            
            # Check if user has non-zero balance globally
            net_balance = user.get_net_balance()
            if abs(net_balance) > 0.01:
                balance_url = url_for('dashboard.home')
                if net_balance > 0:
                    reasons.append(
                        f"{user.name} is owed <strong>${net_balance:.2f}</strong> "
                        f"(<a href='{balance_url}'>view balances</a>)"
                    )
                else:
                    reasons.append(
                        f"{user.name} owes <strong>${abs(net_balance):.2f}</strong> "
                        f"(<a href='{balance_url}'>view balances</a>)"
                    )
        
        can_delete = len(reasons) == 0
        return can_delete, reasons
    
    @staticmethod
    def delete_user(user_id, group_id=None):
        """
        Delete user or remove from group after validation
        
        Args:
            user_id: ID of user to delete/remove
            group_id: If provided, remove from group instead of deleting user
        
        Returns:
            tuple: (success_boolean, error_message)
        """
        try:
            can_delete, reasons = UserService.can_delete_user(user_id, group_id)
            if not can_delete:
                return False, "<br>".join(reasons)
            
            user = User.query.get_or_404(user_id)
            
            if group_id:
                # Remove from group
                group = Group.query.get_or_404(group_id)
                group.remove_member(user)
                db.session.commit()
                return True, f"Removed {user.name} from {group.name}"
            else:
                # Delete user completely
                db.session.delete(user)
                db.session.commit()
                return True, f"Deleted user {user.name}"
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def add_user_to_group(user_id, group_id, role='member'):
        """
        Add an existing user to a group
        
        Returns:
            tuple: (success_boolean, error_message)
        """
        try:
            user = User.query.get_or_404(user_id)
            group = Group.query.get_or_404(group_id)
            
            if user in group.members:
                return False, f"{user.name} is already a member of {group.name}"
            
            group.add_member(user, role)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)