# app/services/expense_service.py - UPDATED for group-based expense tracking

from models import db, Expense, User, Category, ExpenseParticipant, Group, Balance
from datetime import datetime
from sqlalchemy import func

class ExpenseService:
    
    @staticmethod
    def create_group_expense(expense_data):
        """
        Create expense within a group with validation and balance updates
        
        Args:
            expense_data: dict with keys: amount, payer_id, participant_ids, 
                         category_id, category_description, date, group_id
        
        Returns:
            tuple: (expense_object, errors_list)
        """
        errors = []
        
        # Extract and validate data
        amount = expense_data.get('amount')
        payer_id = expense_data.get('payer_id')
        participant_ids = expense_data.get('participant_ids', [])
        category_id = expense_data.get('category_id')
        category_description = expense_data.get('category_description')
        date_str = expense_data.get('date')
        group_id = expense_data.get('group_id')
        
        # Group validation
        if not group_id:
            errors.append("Group ID is required")
            return None, errors
        
        group = Group.query.get(group_id)
        if not group:
            errors.append("Invalid group")
            return None, errors
        
        # Validation
        try:
            amount = float(amount)
            if amount <= 0:
                errors.append("Amount must be positive")
        except (ValueError, TypeError):
            errors.append("Amount must be a number")
        
        if not payer_id:
            errors.append("Please select a valid user")
        
        if not category_id:
            errors.append("Please select a valid category")
        
        if not participant_ids:
            errors.append("Please select at least one participant")
        
        # Date validation
        if date_str:
            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Use YYYY-MM-DD")
                expense_date = datetime.now().date()
        else:
            expense_date = datetime.now().date()
        
        # Return errors if any validation failed
        if errors:
            return None, errors
        
        # Convert IDs to integers and validate
        try:
            participant_ids = [int(pid) for pid in participant_ids]
            payer_id = int(payer_id)
            category_id = int(category_id)
            group_id = int(group_id)
        except ValueError:
            errors.append("Invalid user or category selection")
            return None, errors
        
        # Verify payer is group member
        payer = User.query.get(payer_id)
        if not payer or payer not in group.members:
            errors.append("Payer must be a group member")
            return None, errors
        
        # Verify all participants are group members
        for pid in participant_ids:
            participant_user = User.query.get(pid)
            if not participant_user or participant_user not in group.members:
                errors.append(f"All participants must be group members")
                return None, errors
        
        # Verify category belongs to group
        category = Category.query.get(category_id)
        if not category or category.group_id != group_id:
            errors.append("Category must belong to the group")
            return None, errors
        
        try:
            # Create the expense
            expense = Expense(
                amount=amount,
                category_id=category_id,
                category_description=category_description,
                user_id=payer_id,
                group_id=group_id,
                date=expense_date,
                split_type='equal'
            )
            
            db.session.add(expense)
            db.session.flush()  # Get the expense ID
            
            # Create participants with equal split
            individual_share = amount / len(participant_ids)
            
            for user_id in participant_ids:
                participant = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount_owed=individual_share
                )
                db.session.add(participant)
            
            db.session.commit()
            
            # Recalculate group balances
            ExpenseService._recalculate_group_balances(group_id)
            
            return expense, []
            
        except Exception as e:
            db.session.rollback()
            return None, [f"Failed to create expense: {str(e)}"]
    
    @staticmethod
    def _recalculate_group_balances(group_id):
        """Recalculate balances for a specific group"""
        from app.services.balance_service import BalanceService
        
        # Clear existing group balances
        Balance.query.filter_by(group_id=group_id).delete()
        
        # Get group members
        group = Group.query.get(group_id)
        if not group:
            return
        
        member_ids = [member.id for member in group.members]
        
        # Initialize balances for all group members
        for member_id in member_ids:
            balance = Balance(
                user_id=member_id,
                group_id=group_id,
                amount=0.0
            )
            db.session.add(balance)
        
        # Calculate balances from expenses
        group_expenses = Expense.query.filter_by(group_id=group_id).all()
        
        for expense in group_expenses:
            payer_id = expense.user_id
            
            # Payer gets credited for the full amount
            payer_balance = Balance.query.filter_by(
                user_id=payer_id, 
                group_id=group_id
            ).first()
            if payer_balance:
                payer_balance.amount += expense.amount
            
            # Each participant owes their share
            for participant in expense.participants:
                participant_balance = Balance.query.filter_by(
                    user_id=participant.user_id,
                    group_id=group_id
                ).first()
                if participant_balance:
                    participant_balance.amount -= participant.amount_owed
        
        # Process group settlements
        from models import Settlement
        group_settlements = Settlement.query.filter_by(group_id=group_id).all()
        
        for settlement in group_settlements:
            # Payer balance decreases (they paid money)
            payer_balance = Balance.query.filter_by(
                user_id=settlement.payer_id,
                group_id=group_id
            ).first()
            if payer_balance:
                payer_balance.amount += settlement.amount
            
            # Receiver balance increases (they received money)
            receiver_balance = Balance.query.filter_by(
                user_id=settlement.receiver_id,
                group_id=group_id
            ).first()
            if receiver_balance:
                receiver_balance.amount -= settlement.amount
        
        # Update timestamps
        for balance in Balance.query.filter_by(group_id=group_id).all():
            balance.last_updated = datetime.utcnow()
        
        db.session.commit()
    
    @staticmethod
    def update_expense(expense_id, update_data):
        """
        Update expense and recalculate group balances
        """
        try:
            expense = Expense.query.get_or_404(expense_id)
            original_group_id = expense.group_id
            
            # Update fields
            if 'amount' in update_data:
                expense.amount = float(update_data['amount'])
                
            if 'category' in update_data:
                if expense.group_id:
                    # For group expenses, find category within the group
                    category = Category.query.filter_by(
                        name=update_data['category'], 
                        group_id=expense.group_id
                    ).first()
                else:
                    # Legacy personal expense
                    category = Category.query.filter_by(name=update_data['category']).first()
                
                if category:
                    expense.category_id = category.id
                    
            if 'user' in update_data:
                user = User.query.filter_by(name=update_data['user']).first()
                if user:
                    # For group expenses, verify user is group member
                    if expense.group_id:
                        group = Group.query.get(expense.group_id)
                        if user not in group.members:
                            return False, "User must be a group member"
                    expense.user_id = user.id
                    
            if 'description' in update_data:
                expense.category_description = update_data['description']
                
            if 'date' in update_data:
                expense.date = datetime.strptime(update_data['date'], '%Y-%m-%d').date()
            
            # Handle participants if provided
            if 'participants' in update_data:
                # Remove old participants
                for p in expense.participants:
                    db.session.delete(p)
                db.session.flush()
                
                # Add new participants (verify group membership for group expenses)
                participant_count = len(update_data['participants'])
                if participant_count > 0:
                    if expense.group_id:
                        group = Group.query.get(expense.group_id)
                        for user_id in update_data['participants']:
                            user = User.query.get(user_id)
                            if not user or user not in group.members:
                                return False, "All participants must be group members"
                    
                    individual_share = expense.amount / participant_count
                    for user_id in update_data['participants']:
                        participant = ExpenseParticipant(
                            expense_id=expense.id, 
                            user_id=user_id, 
                            amount_owed=individual_share
                        )
                        db.session.add(participant)
            else:
                # Recalculate existing participant amounts
                participant_count = len(expense.participants)
                if participant_count > 0:
                    individual_share = expense.amount / participant_count
                    for participant in expense.participants:
                        participant.amount_owed = individual_share
            
            # Commit changes
            db.session.commit()
            
            # Recalculate balances for the affected group
            if expense.group_id:
                ExpenseService._recalculate_group_balances(expense.group_id)
            else:
                # Legacy personal expense - recalculate all balances
                from app.services.balance_service import BalanceService
                BalanceService.recalculate_all_balances()
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def delete_expense(expense_id):
        """
        Delete expense and recalculate balances
        """
        try:
            expense = Expense.query.get_or_404(expense_id)
            group_id = expense.group_id
            
            # Delete expense (participants will be deleted via cascade)
            db.session.delete(expense)
            db.session.commit()
            
            # Recalculate balances for the affected group
            if group_id:
                ExpenseService._recalculate_group_balances(group_id)
            else:
                # Legacy personal expense - recalculate all balances
                from app.services.balance_service import BalanceService
                BalanceService.recalculate_all_balances()
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def get_group_expenses(group_id, limit=None):
        """Get expenses for a specific group"""
        query = Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_all_expenses():
        """Get all expenses ordered by date (legacy method)"""
        return Expense.query.order_by(Expense.date.desc()).all()
    
    @staticmethod
    def get_user_expenses(user_id, group_id=None):
        """Get expenses for a user, optionally within a group"""
        query = Expense.query.filter_by(user_id=user_id)
        
        if group_id:
            query = query.filter_by(group_id=group_id)
        
        return query.order_by(Expense.date.desc()).all()
    
    @staticmethod
    def get_store_suggestions(query, group_id=None):
        """Get store/description suggestions based on query, optionally filtered by group"""
        if not query:
            return []
        
        base_query = Expense.query.filter(
            Expense.category_description.ilike(f"%{query}%")
        )
        
        if group_id:
            base_query = base_query.filter_by(group_id=group_id)
        
        matches = base_query.with_entities(Expense.category_description)\
            .distinct().limit(10).all()
        
        return [m[0] for m in matches if m[0]]
    
    @staticmethod
    def get_group_statistics(group_id):
        """Get statistics for a group"""
        # Total expenses this month
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_total = db.session.query(func.sum(Expense.amount)).filter(
            Expense.group_id == group_id,
            Expense.date >= start_of_month.date()
        ).scalar() or 0
        
        # Total expenses ever
        total_spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.group_id == group_id
        ).scalar() or 0
        
        # Number of expenses
        expense_count = Expense.query.filter_by(group_id=group_id).count()
        
        return {
            'monthly_total': monthly_total,
            'total_spent': total_spent,
            'expense_count': expense_count
        }
    
    # Legacy methods for backward compatibility
    @staticmethod
    def create_expense(expense_data):
        """
        Legacy method - creates expense without group context
        This is kept for backward compatibility with existing code
        """
        errors = []
        
        # Extract and validate data
        amount = expense_data.get('amount')
        payer_id = expense_data.get('payer_id')
        participant_ids = expense_data.get('participant_ids', [])
        category_id = expense_data.get('category_id')
        category_description = expense_data.get('category_description')
        date_str = expense_data.get('date')
        
        # Validation
        try:
            amount = float(amount)
            if amount <= 0:
                errors.append("Amount must be positive")
        except (ValueError, TypeError):
            errors.append("Amount must be a number")
        
        if not payer_id:
            errors.append("Please select a valid user")
        
        if not category_id:
            errors.append("Please select a valid category")
        
        if not participant_ids:
            errors.append("Please select at least one participant")
        
        # Date validation
        if date_str:
            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Use YYYY-MM-DD")
                expense_date = datetime.now().date()
        else:
            expense_date = datetime.now().date()
        
        # Return errors if any validation failed
        if errors:
            return None, errors
        
        # Convert participant IDs to integers
        try:
            participant_ids = [int(pid) for pid in participant_ids]
            payer_id = int(payer_id)
            category_id = int(category_id)
        except ValueError:
            errors.append("Invalid user or category selection")
            return None, errors
        
        # Create expense using legacy balance service
        from app.services.balance_service import BalanceService
        expense = BalanceService.create_expense_with_participants(
            amount=amount,
            payer_id=payer_id,
            participant_ids=participant_ids,
            category_id=category_id,
            category_description=category_description,
            date=expense_date
        )
        
        if expense:
            return expense, []
        else:
            return None, ["Failed to create expense. Please try again."]