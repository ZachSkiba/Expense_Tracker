from models import db, User
from flask import url_for

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
    def create_user(name):
        """
        Create a new user
        
        Returns:
            tuple: (user_object, error_message)
        """
        name = name.strip()
        if not name:
            return None, "Name cannot be empty"
        
        if User.query.filter_by(name=name).first():
            return None, f"User '{name}' already exists"
        
        try:
            new_user = User(name=name)
            db.session.add(new_user)
            db.session.commit()
            return new_user, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def can_delete_user(user_id):
        """Check if user can be safely deleted"""
        user = User.query.get_or_404(user_id)
        reasons = []
        
        # Check if user has expenses as payer
        payer_expenses = user.expenses
        if payer_expenses:
            expense_url = url_for('expenses.add_expense')
            reasons.append(
                f"{user.name} paid for "
                f"<a href='{expense_url}'>{len(payer_expenses)} expense(s)</a>"
            )
        
        # Check if user has non-zero balance
        net_balance = user.get_net_balance()
        if abs(net_balance) > 0.01:  # Not zero (accounting for floating point)
            balance_url = url_for('balances.combined_balances_settlements')
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
    def delete_user(user_id):
        """
        Delete user after validation
        
        Returns:
            tuple: (success_boolean, error_message)
        """
        try:
            can_delete, reasons = UserService.can_delete_user(user_id)
            if not can_delete:
                return False, "<br>".join(reasons)
            
            user = User.query.get_or_404(user_id)
            db.session.delete(user)
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)