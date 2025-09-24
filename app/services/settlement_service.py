# app/services/settlement_service.py - UPDATED to be group-aware

from models import db, Settlement, User
from app.services.balance_service import BalanceService
from datetime import datetime

class SettlementService:
    
    @staticmethod
    def create_settlement(settlement_data):
        """
        Create a settlement/payment between users and recalculate balances
        UPDATED: Now group-aware
        """
        errors = []
        
        # Extract and validate data
        amount = settlement_data.get('amount')
        payer_id = settlement_data.get('payer_id')
        receiver_id = settlement_data.get('receiver_id')
        description = settlement_data.get('description', '').strip()
        date_str = settlement_data.get('date')
        group_id = settlement_data.get('group_id')  # NEW: Group context
        
        # Validation
        try:
            amount = float(amount)
            if amount <= 0:
                errors.append("Amount must be positive")
        except (ValueError, TypeError):
            errors.append("Amount must be a number")
        
        if not payer_id:
            errors.append("Please select who is paying")
        
        if not receiver_id:
            errors.append("Please select who is receiving payment")
            
        if payer_id == receiver_id:
            errors.append("Payer and receiver cannot be the same person")
        
        # Date validation
        if date_str:
            try:
                settlement_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Use YYYY-MM-DD")
                settlement_date = datetime.now().date()
        else:
            settlement_date = datetime.now().date()
        
        # Return errors if any validation failed
        if errors:
            return None, errors
        
        # Convert IDs to integers
        try:
            payer_id = int(payer_id)
            receiver_id = int(receiver_id)
            if group_id:
                group_id = int(group_id)
        except ValueError:
            errors.append("Invalid user selection")
            return None, errors
        
        # Verify users exist
        payer = User.query.get(payer_id)
        receiver = User.query.get(receiver_id)
        if not payer or not receiver:
            errors.append("Invalid user selection")
            return None, errors
        
        # If group specified, verify users are group members
        if group_id:
            from models import Group
            group = Group.query.get(group_id)
            if not group:
                errors.append("Invalid group")
                return None, errors
            
            if payer not in group.members or receiver not in group.members:
                errors.append("Both users must be group members")
                return None, errors
        
        try:
            # Create settlement record
            settlement = Settlement(
                amount=amount,
                payer_id=payer_id,
                receiver_id=receiver_id,
                group_id=group_id,  # NEW: Add group context
                description=description if description else None,
                date=settlement_date
            )
            db.session.add(settlement)
            db.session.commit()
            
            # Recalculate balances - group-aware or all balances
            if group_id:
                # Use the new group-specific recalculation
                from app.services.expense_service import ExpenseService
                ExpenseService._recalculate_group_balances(group_id)
            else:
                # Legacy: recalculate all balances
                BalanceService.recalculate_all_balances()
            
            return settlement, []
            
        except Exception as e:
            db.session.rollback()
            return None, [f"Failed to create settlement: {str(e)}"]
    
    @staticmethod
    def get_all_settlements(group_id=None):
        """Get settlements, optionally filtered by group"""
        query = Settlement.query.order_by(Settlement.date.desc(), Settlement.created_at.desc())
        
        if group_id:
            query = query.filter_by(group_id=group_id)
        
        return query.all()
    
    @staticmethod
    def get_recent_settlements(group_id=None, limit=10):
        """Get recent settlements for display, optionally filtered by group"""
        settlements = SettlementService.get_all_settlements(group_id)[:limit]
        
        result = []
        for settlement in settlements:
            result.append({
                'id': settlement.id,
                'amount': settlement.amount,
                'payer_name': settlement.payer.name,
                'receiver_name': settlement.receiver.name,
                'description': settlement.description,
                'date': settlement.date.strftime('%Y-%m-%d'),
                'created_at': settlement.created_at
            })
        
        return result
    
    @staticmethod
    def delete_settlement(settlement_id):
        """
        Delete settlement and recalculate balances
        UPDATED: Now group-aware
        """
        try:
            settlement = Settlement.query.get_or_404(settlement_id)
            group_id = settlement.group_id
            
            # Delete settlement
            db.session.delete(settlement)
            db.session.commit()
            
            # Recalculate balances for affected group or all
            if group_id:
                from app.services.expense_service import ExpenseService
                ExpenseService._recalculate_group_balances(group_id)
            else:
                BalanceService.recalculate_all_balances()
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def update_settlement(settlement_id, update_data):
        """
        Update settlement and recalculate balances
        UPDATED: Now group-aware
        """
        try:
            settlement = Settlement.query.get_or_404(settlement_id)
            group_id = settlement.group_id
            
            # Update fields
            if 'amount' in update_data:
                settlement.amount = float(update_data['amount'])
                
            if 'payer' in update_data:
                user = User.query.filter_by(name=update_data['payer']).first()
                if user:
                    settlement.payer_id = user.id
                    
            if 'receiver' in update_data:
                user = User.query.filter_by(name=update_data['receiver']).first()
                if user:
                    settlement.receiver_id = user.id
                    
            if 'description' in update_data:
                settlement.description = update_data['description'] if update_data['description'] else None
                
            if 'date' in update_data:
                settlement.date = datetime.strptime(update_data['date'], '%Y-%m-%d').date()
            
            db.session.commit()
            
            # Recalculate balances for affected group or all
            if group_id:
                from app.services.expense_service import ExpenseService
                ExpenseService._recalculate_group_balances(group_id)
            else:
                BalanceService.recalculate_all_balances()
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def get_settlement_data(group_id=None):
        """Get all settlements as list of dicts for JSON/template use"""
        settlements = SettlementService.get_all_settlements(group_id)
        return [{
            'id': s.id,
            'amount': s.amount,
            'payer_name': s.payer.name,
            'receiver_name': s.receiver.name,
            'description': s.description,
            'date': s.date.strftime('%Y-%m-%d'),
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M')
        } for s in settlements]