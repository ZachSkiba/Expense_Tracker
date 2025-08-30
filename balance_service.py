from models import db, User, Expense, ExpenseParticipant, Balance, Settlement
from datetime import datetime
from sqlalchemy.exc import IntegrityError

class BalanceService:
    
    @staticmethod
    def create_expense_with_participants(amount, payer_id, participant_ids, category_id, 
                                       category_description=None, date=None, split_type='equal'):
        """
        Create a new expense and recalculate all balances
        
        Args:
            amount: Total expense amount
            payer_id: ID of user who paid
            participant_ids: List of user IDs who participated (including payer if they participated)
            category_id: Category ID
            category_description: Optional description
            date: Expense date (defaults to today)
            split_type: How to split the expense ('equal' or 'custom')
        
        Returns:
            Expense object or None if error
        """
        try:
            # Validate inputs
            if not participant_ids:
                raise ValueError("At least one participant is required")
            
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            # Create expense
            expense = Expense(
                amount=amount,
                user_id=payer_id,
                category_id=category_id,
                category_description=category_description,
                date=date or datetime.now().date(),
                split_type=split_type
            )
            db.session.add(expense)
            db.session.flush()  # Get the expense ID
            
            # Calculate individual shares
            if split_type == 'equal':
                individual_share = amount / len(participant_ids)
                participant_amounts = {pid: individual_share for pid in participant_ids}
            else:
                # For custom splits, you'd pass in participant_amounts directly
                raise NotImplementedError("Custom splits not implemented yet")
            
            # Create participant records
            for participant_id in participant_ids:
                participant = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=participant_id,
                    amount_owed=participant_amounts[participant_id]
                )
                db.session.add(participant)
            
            db.session.commit()
            
            # Recalculate ALL balances to ensure accuracy
            BalanceService.recalculate_all_balances()
            
            return expense
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating expense: {e}")
            return None
    
    @staticmethod
    def _update_user_balance(user_id, amount):
        """Update a single user's balance"""
        
        # Get or create balance record
        balance = Balance.query.filter_by(user_id=user_id).first()
        if not balance:
            balance = Balance(user_id=user_id, amount=0.0)
            db.session.add(balance)
        
        # Update balance
        balance.amount += amount
        balance.last_updated = datetime.utcnow()
    
    @staticmethod
    def get_all_balances():
        """Get current balances for all users"""
        balances = db.session.query(
            User.id,
            User.name,
            Balance.amount,
            Balance.last_updated
        ).outerjoin(Balance, User.id == Balance.user_id).all()
        
        result = []
        for user_id, user_name, balance_amount, last_updated in balances:
            result.append({
                'user_id': user_id,
                'user_name': user_name,
                'balance': float(balance_amount or 0.0),
                'status': 'owed' if (balance_amount or 0) > 0 else 'owes' if (balance_amount or 0) < 0 else 'even',
                'last_updated': last_updated.isoformat() if last_updated else None
            })
        
        return result
    
    @staticmethod
    def get_settlement_suggestions():
        """Calculate optimal settlements to minimize transactions"""
        balances = BalanceService.get_all_balances()
        
        # Separate creditors (positive balance) and debtors (negative balance)
        creditors = [(b['user_name'], b['balance']) for b in balances if b['balance'] > 0.01]
        debtors = [(b['user_name'], abs(b['balance'])) for b in balances if b['balance'] < -0.01]
        
        # Sort by amount (largest first)
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)
        
        settlements = []
        i, j = 0, 0
        
        while i < len(creditors) and j < len(debtors):
            creditor_name, credit_amount = creditors[i]
            debtor_name, debt_amount = debtors[j]
            
            # Settle the smaller amount
            settlement_amount = min(credit_amount, debt_amount)
            
            settlements.append({
                'from': debtor_name,
                'to': creditor_name,
                'amount': round(settlement_amount, 2)
            })
            
            # Update amounts
            creditors[i] = (creditor_name, credit_amount - settlement_amount)
            debtors[j] = (debtor_name, debt_amount - settlement_amount)
            
            # Move to next if fully settled
            if creditors[i][1] < 0.01:
                i += 1
            if debtors[j][1] < 0.01:
                j += 1
        
        return settlements
    
    @staticmethod
    def recalculate_all_balances():
        """
        Recalculate all balances from scratch including both expenses AND settlements
        This ensures complete accuracy by rebuilding all balance data
        """
        try:
            # Delete all existing balances
            db.session.query(Balance).delete()
            db.session.flush()

            # Process all expenses
            expenses = db.session.query(Expense).all()
            for expense in expenses:
                participants = expense.participants
                if not participants:
                    continue
                
                # Credit the payer with the full amount they paid
                BalanceService._update_user_balance(expense.user_id, expense.amount)
                
                # Debit each participant their share
                for participant in participants:
                    BalanceService._update_user_balance(participant.user_id, -participant.amount_owed)
            
            # Process all settlements
            settlements = db.session.query(Settlement).all()
            for settlement in settlements:
                # Payer's balance decreases (they paid money out)
                BalanceService._update_user_balance(settlement.payer_id, -settlement.amount)
                # Receiver's balance increases (they received money)
                BalanceService._update_user_balance(settlement.receiver_id, settlement.amount)

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error recalculating balances: {e}")
            return False
        
    @staticmethod
    def reverse_balances_for_expense(expense):
        """
        Reverse the balance effects of a given expense.
        After this, recalculate_all_balances() should be called.
        """
        # This method is now simplified since we always do full recalculation
        # Just mark that we need to recalculate everything
        pass