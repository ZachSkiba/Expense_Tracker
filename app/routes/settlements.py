from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from app.services.settlement_service import SettlementService
from app.services.user_service import UserService
from models import db, Settlement, User
from balance_service import BalanceService
from datetime import datetime

settlements_bp = Blueprint("settlements", __name__)

@settlements_bp.route("/api/settlements", methods=["POST"])
def add_settlement_api():
    """API endpoint to add new settlement"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'payer_id', 'receiver_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create settlement
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

@settlements_bp.route("/api/settlements", methods=["GET"])
def get_settlements_api():
    """API endpoint to get recent settlements"""
    try:
        limit = request.args.get('limit', 10, type=int)
        settlements = SettlementService.get_recent_settlements(limit)
        return jsonify({'settlements': settlements}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settlements_bp.route("/settlements", methods=["GET", "POST"])
def manage_settlements():
    """Web page to manage settlements"""
    error = None
    users_data = UserService.get_all_data()
    settlements_data = SettlementService.get_settlement_data()

    if request.method == "POST":
        # Handle form submission
        settlement_data = {
            'amount': request.form.get('amount'),
            'payer_id': request.form.get('payer_id'),
            'receiver_id': request.form.get('receiver_id'),
            'description': request.form.get('description'),
            'date': request.form.get('date') or datetime.today().strftime('%Y-%m-%d')
        }

        # Use service to create settlement
        settlement, errors = SettlementService.create_settlement(settlement_data)
        
        if settlement:
            return redirect(url_for("settlements.manage_settlements"))
        else:
            # Handle errors
            error = "; ".join(errors)
            return render_template("settlements.html", 
                                 error=error, 
                                 users=users_data, 
                                 settlements=settlements_data,
                                 # Preserve form data
                                 amount=settlement_data.get('amount'),
                                 payer_id=settlement_data.get('payer_id'),
                                 receiver_id=settlement_data.get('receiver_id'),
                                 description=settlement_data.get('description'),
                                 date=settlement_data.get('date'))

    return render_template("settlements.html", 
                         error=None, 
                         users=users_data, 
                         settlements=settlements_data)

@settlements_bp.route("/delete_settlement/<int:settlement_id>", methods=["POST"])
def delete_settlement(settlement_id):
    """Delete settlement and reverse balance changes"""
    success, error = SettlementService.delete_settlement(settlement_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error})

@settlements_bp.route("/edit_settlement/<int:settlement_id>", methods=["POST"])
def edit_settlement(settlement_id):
    """Edit settlement and recalculate balances as needed"""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    try:
        settlement = Settlement.query.get_or_404(settlement_id)
        
        # Store old values for balance reversal
        old_amount = settlement.amount
        old_payer_id = settlement.payer_id
        old_receiver_id = settlement.receiver_id
        
        # Reverse old balance changes
        BalanceService._update_user_balance(old_payer_id, old_amount)
        BalanceService._update_user_balance(old_receiver_id, -old_amount)
        
        # Update fields
        if 'amount' in data:
            settlement.amount = float(data['amount'])
            
        if 'payer' in data:
            user = User.query.filter_by(name=data['payer']).first()
            if user:
                settlement.payer_id = user.id
                
        if 'receiver' in data:
            user = User.query.filter_by(name=data['receiver']).first()
            if user:
                settlement.receiver_id = user.id
                
        if 'description' in data:
            settlement.description = data['description'] if data['description'] else None
            
        if 'date' in data:
            settlement.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        
        # Apply new balance changes
        BalanceService._update_user_balance(settlement.payer_id, -settlement.amount)
        BalanceService._update_user_balance(settlement.receiver_id, settlement.amount)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500