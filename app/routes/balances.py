# app/routes/balances.py - UPDATED with group filtering

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app.services.balance_service import BalanceService
from app.services.settlement_service import SettlementService
from app.services.user_service import UserService
from models import Group, db, User, Category, Balance, Settlement
from datetime import datetime
from sqlalchemy import func
from flask_login import current_user, login_required

balances_bp = Blueprint("balances", __name__)

# UPDATED: Group-aware API endpoints
@balances_bp.route("/api/balances", methods=["GET"])
@balances_bp.route("/api/balances/<int:group_id>", methods=["GET"])
def get_balances_api(group_id=None):
    """API endpoint to get current balances - group-aware"""
    try:
        if group_id:
            # Get balances for specific group
            balances = Balance.query.filter_by(group_id=group_id).join(User).all()
            balance_data = []
            for balance in balances:
                if abs(balance.amount) > 0.01:  # Only show non-zero balances
                    balance_data.append({
                        'user_id': balance.user_id,
                        'user_name': balance.user.name,
                        'balance': round(balance.amount, 2)
                    })
        else:
            # Fallback to legacy behavior for backward compatibility
            balances = BalanceService.get_all_balances()
            balance_data = balances
        
        return jsonify({'balances': balance_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@balances_bp.route("/api/settlement-suggestions", methods=["GET"])
@balances_bp.route("/api/settlement-suggestions/<int:group_id>", methods=["GET"])
def get_settlement_suggestions_api(group_id=None):
    """API endpoint to get settlement suggestions - group-aware"""
    try:
        if group_id:
            # Get group-specific settlement suggestions
            balances = Balance.query.filter_by(group_id=group_id).join(User).all()
            
            suggestions = []
            debtors = []
            creditors = []
            
            # Calculate who owes what
            for balance in balances:
                if balance.amount < -0.01:
                    debtors.append({
                        'user_id': balance.user_id,
                        'from': balance.user.name,  # Use 'from' for compatibility
                        'amount': abs(balance.amount)
                    })
                elif balance.amount > 0.01:
                    creditors.append({
                        'user_id': balance.user_id,
                        'to': balance.user.name,  # Use 'to' for compatibility
                        'amount': balance.amount
                    })
            
            # Sort by amount (largest first)
            debtors.sort(key=lambda x: x['amount'], reverse=True)
            creditors.sort(key=lambda x: x['amount'], reverse=True)
            
            # Calculate minimal settlements
            i, j = 0, 0
            while i < len(debtors) and j < len(creditors):
                debtor = debtors[i]
                creditor = creditors[j]
                
                settlement_amount = min(debtor['amount'], creditor['amount'])
                
                if settlement_amount > 0.01:
                    suggestions.append({
                        'from': debtor['from'],
                        'to': creditor['to'],
                        'amount': round(settlement_amount, 2)
                    })
                
                debtor['amount'] -= settlement_amount
                creditor['amount'] -= settlement_amount
                
                if debtor['amount'] <= 0.01:
                    i += 1
                if creditor['amount'] <= 0.01:
                    j += 1
        else:
            # Fallback to legacy behavior
            suggestions = BalanceService.get_settlement_suggestions()
        
        return jsonify({'suggestions': suggestions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@balances_bp.route("/api/settlements", methods=["GET"])
@balances_bp.route("/api/settlements/<int:group_id>", methods=["GET"])
def get_settlements_api(group_id=None):
    """API endpoint to get all settlements data - group-aware"""
    try:
        if group_id:
            # Get group-specific settlements
            settlements = Settlement.query.filter_by(group_id=group_id)\
                .order_by(Settlement.date.desc()).limit(10).all()
            
            settlements_data = []
            for settlement in settlements:
                settlements_data.append({
                    'id': settlement.id,
                    'amount': round(settlement.amount, 2),
                    'payer_name': settlement.payer.name,
                    'receiver_name': settlement.receiver.name,
                    'description': settlement.description or '',
                    'date': settlement.date.strftime('%Y-%m-%d')
                })
        else:
            # Fallback to legacy behavior
            settlements_data = SettlementService.get_settlement_data()
        
        return jsonify({'settlements': settlements_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# UPDATED: Group-aware settlement creation
@balances_bp.route("/api/settlements", methods=["POST"])
@balances_bp.route("/api/settlements/<int:group_id>", methods=["POST"])
def add_settlement_api(group_id=None):
    """API endpoint to add new settlement - group-aware"""
    try:
        data = request.get_json()
        
        # If group_id provided in URL, use it; otherwise get from data
        if group_id:
            data['group_id'] = group_id
        
        # Validate required fields
        required_fields = ['amount', 'payer_id', 'receiver_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # If group_id specified, verify users are members
        if 'group_id' in data and data['group_id']:
            group = Group.query.get(data['group_id'])
            if not group:
                return jsonify({'error': 'Invalid group'}), 400
            
            payer = User.query.get(data['payer_id'])
            receiver = User.query.get(data['receiver_id'])
            
            if not payer or payer not in group.members:
                return jsonify({'error': 'Payer must be a group member'}), 400
            if not receiver or receiver not in group.members:
                return jsonify({'error': 'Receiver must be a group member'}), 400
            if payer.id == receiver.id:
                return jsonify({'error': 'Payer and receiver cannot be the same person'}), 400
        
        # Create settlement using service (which will recalculate balances)
        settlement, errors = SettlementService.create_settlement(data)
        
        if settlement:
            return jsonify({
                'success': True,
                'settlement_id': settlement.id,
                'message': 'Settlement recorded successfully'
            }), 201
        else:
            return jsonify({'error': '; '.join(errors)}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Keep existing routes for backward compatibility
@balances_bp.route("/balances")
def balances_page():
    """Web page to view balances - render redirect template"""
    return render_template("balances.html")

@balances_bp.route("/api/balances/recalculate", methods=["POST"])
def recalculate_balances():
    """Manually recalculate all balances from expenses and settlements (admin function)"""
    try:
        success = BalanceService.recalculate_all_balances()
        if success:
            return jsonify({'message': 'Balances recalculated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to recalculate balances'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@balances_bp.route("/balances-settlements/<int:group_id>", methods=["GET", "POST"])
def combined_balances_settlements(group_id):
    """Combined balances and settlements management page - group-aware"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    # Recalculate balances for this group
    from app.services.expense_service import ExpenseService
    ExpenseService._recalculate_group_balances(group_id)
    
    error = None
    users_data = [{'id': u.id, 'name': u.name} for u in group.members]
    
    # Handle settlement form submission
    if request.method == "POST":
        settlement_data = {
            'amount': request.form.get('amount'),
            'payer_id': request.form.get('payer_id'),
            'receiver_id': request.form.get('receiver_id'),
            'description': request.form.get('description'),
            'date': request.form.get('date') or datetime.today().strftime('%Y-%m-%d'),
            'group_id': group_id  # Add group context
        }

        # Use service to create settlement (which will recalculate balances)
        settlement, errors = SettlementService.create_settlement(settlement_data)
        
        if settlement:
            return redirect(url_for("balances.combined_balances_settlements", group_id=group_id))
        else:
            # Handle errors
            error = "; ".join(errors)
    
    # Get group-specific data
    balances = Balance.query.filter_by(group_id=group_id).join(User).all()
    balance_data = []
    for balance in balances:
        if abs(balance.amount) > 0.01:
            balance_data.append({
                'user_id': balance.user_id,
                'user_name': balance.user.name,
                'balance': round(balance.amount, 2)
            })
    
    # Get settlement suggestions for this group (reuse the logic from API)
    debtors = []
    creditors = []
    for balance in balances:
        if balance.amount < -0.01:
            debtors.append({'from': balance.user.name, 'amount': abs(balance.amount)})
        elif balance.amount > 0.01:
            creditors.append({'to': balance.user.name, 'amount': balance.amount})
    
    debtors.sort(key=lambda x: x['amount'], reverse=True)
    creditors.sort(key=lambda x: x['amount'], reverse=True)
    
    settlements = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        settlement_amount = min(debtor['amount'], creditor['amount'])
        
        if settlement_amount > 0.01:
            settlements.append({
                'from': debtor['from'],
                'to': creditor['to'],
                'amount': round(settlement_amount, 2)
            })
        
        debtor['amount'] -= settlement_amount
        creditor['amount'] -= settlement_amount
        
        if debtor['amount'] <= 0.01:
            i += 1
        if creditor['amount'] <= 0.01:
            j += 1
    
    # Get recent settlements for the payments history table
    recent_settlements = Settlement.query.filter_by(group_id=group_id)\
        .order_by(Settlement.date.desc()).limit(10).all()
    
    settlements_data = []
    for settlement in recent_settlements:
        settlements_data.append({
            'id': settlement.id,
            'amount': round(settlement.amount, 2),
            'payer_name': settlement.payer.name,
            'receiver_name': settlement.receiver.name,
            'description': settlement.description or '',
            'date': settlement.date.strftime('%Y-%m-%d')
        })
    
    return render_template("combined_balances_settlements.html", 
                         error=error,
                         users=users_data,
                         balances=balance_data,
                         settlements=settlements,  # Settlement suggestions
                         settlements_data=settlements_data,  # Actual payment history
                         group=group,
                         # Preserve form data on error
                         amount=request.form.get('amount') if error else None,
                         payer_id=request.form.get('payer_id') if error else None,
                         receiver_id=request.form.get('receiver_id') if error else None,
                         description=request.form.get('description') if error else None,
                         date=request.form.get('date') if error else None)