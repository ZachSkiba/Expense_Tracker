from models import db, User, Expense, ExpenseParticipant, Balance, Settlement
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import threading

class BalanceService:
    # Thread lock to prevent concurrent balance recalculations
    _lock = threading.Lock()
    
    @staticmethod
    def create_expense_with_participants(amount, payer_id, participant_ids, category_id, 
                                       category_description=None, date=None, split_type='equal'):
        """
        Create a new expense and recalculate all balances
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
        """Get current balances for all users - READ ONLY, no recalculation"""
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
        """
        Calculate optimal settlements to minimize transactions - READ ONLY
        This returns WHO SHOULD PAY WHOM, not actual payment history
        """
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
        THREAD-SAFE: Recalculate all balances from scratch including both expenses AND settlements
        
        Balance Calculation Logic:
        1. Start all balances at $0
        2. For each expense: Payer gets +amount, each participant gets -their_share
        3. For each settlement: Payer gets +amount (owes less), Receiver gets -amount (owed less)
        
        Example walkthrough:
        - Jake pays $100, Jake & Zach participate 50/50
        - After expense: Jake +$50, Zach -$50
        - Zach pays Jake $20
        - After settlement: Jake +$30, Zach -$30 ✓
        """
        with BalanceService._lock:
            try:
                
                
                # Use a database transaction to ensure consistency
                with db.session.begin():
                    # Delete all existing balances
                    db.session.query(Balance).delete()
                    db.session.flush()

                    # Process all expenses first
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
                        # SETTLEMENT LOGIC:
                        # When Zach (payer_id) pays Jake (receiver_id) $20:
                        # - Zach's balance increases by $20 (he owes $20 less)
                        # - Jake's balance decreases by $20 (he is owed $20 less)
                        
                        BalanceService._update_user_balance(settlement.payer_id, settlement.amount)     # Payer owes less (+)
                        BalanceService._update_user_balance(settlement.receiver_id, -settlement.amount) # Receiver owed less (-)
                        
                # Transaction automatically commits here if no exceptions
                return True

            except Exception as e:
                print(f"[ERROR] Error recalculating balances: {e}")
                # Transaction automatically rolls back on exception
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

    @staticmethod
    def get_debug_info():
        """Get debug information about current balances and calculations"""
        try:
            # Get current balances
            balances = BalanceService.get_all_balances()
            
            # Get total expenses per user
            expense_totals = db.session.query(
                User.name,
                func.sum(Expense.amount).label('total_paid')
            ).join(Expense, User.id == Expense.user_id)\
             .group_by(User.id, User.name).all()
            
            # Get total owed per user (from expense participants)
            owed_totals = db.session.query(
                User.name,
                func.sum(ExpenseParticipant.amount_owed).label('total_owed')
            ).join(ExpenseParticipant, User.id == ExpenseParticipant.user_id)\
             .group_by(User.id, User.name).all()
            
            # Get settlements
            settlement_data = db.session.query(Settlement).all()
            
            debug_info = {
                'current_balances': balances,
                'expense_totals': [{'user': name, 'total_paid': float(total or 0)} for name, total in expense_totals],
                'owed_totals': [{'user': name, 'total_owed': float(total or 0)} for name, total in owed_totals],
                'settlements': [{'payer': s.payer.name, 'receiver': s.receiver.name, 'amount': s.amount, 'date': s.date.isoformat()} for s in settlement_data]
            }
            
            return debug_info
            
        except Exception as e:
            return {'error': str(e)}