from models import db, Expense, User, Category, ExpenseParticipant
from balance_service import BalanceService
from datetime import datetime

class ExpenseService:
    
    @staticmethod
    def create_expense(expense_data):
        """
        Create expense with validation and balance updates
        
        Args:
            expense_data: dict with keys: amount, payer_id, participant_ids, 
                         category_id, category_description, date
        
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
        
        # Create expense using BalanceService (which will recalculate all balances)
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
    
    @staticmethod
    def update_expense(expense_id, update_data):
        """
        Update expense and recalculate all balances
        
        Args:
            expense_id: int
            update_data: dict with fields to update
        
        Returns:
            tuple: (success_boolean, error_message)
        """
        try:
            expense = Expense.query.get_or_404(expense_id)
            
            # Update fields
            if 'amount' in update_data:
                expense.amount = float(update_data['amount'])
                
            if 'category' in update_data:
                category = Category.query.filter_by(name=update_data['category']).first()
                if category:
                    expense.category_id = category.id
                    
            if 'user' in update_data:
                user = User.query.filter_by(name=update_data['user']).first()
                if user:
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
                
                # Add new participants
                participant_count = len(update_data['participants'])
                if participant_count > 0:
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
            
            # Recalculate ALL balances from scratch to ensure accuracy
            BalanceService.recalculate_all_balances()
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def delete_expense(expense_id):
        """
        Delete expense and recalculate all balances
        
        Args:
            expense_id: int
        
        Returns:
            tuple: (success_boolean, error_message)
        """
        try:
            expense = Expense.query.get_or_404(expense_id)
            
            # Delete expense (participants will be deleted via cascade)
            db.session.delete(expense)
            db.session.commit()
            
            # Recalculate ALL balances from scratch to ensure accuracy
            BalanceService.recalculate_all_balances()
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def get_all_expenses():
        """Get all expenses ordered by date"""
        return Expense.query.order_by(Expense.date.desc()).all()
    
    @staticmethod
    def get_store_suggestions(query):
        """Get store/description suggestions based on query"""
        if not query:
            return []
        
        matches = (
            Expense.query
            .filter(Expense.category_description.ilike(f"%{query}%"))
            .with_entities(Expense.category_description)
            .distinct()
            .limit(10)
            .all()
        )
        return [m[0] for m in matches if m[0]]