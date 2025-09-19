from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from app.services.settlement_service import SettlementService
from app.services.user_service import UserService
from models import Group, db, Settlement, User
from balance_service import BalanceService
from datetime import datetime

settlements_bp = Blueprint("settlements", __name__)

@settlements_bp.route("/api/settlements/<int:group_id>", methods=["POST"])
def add_settlement_api(group_id):
    """API endpoint to add new settlement"""
    group = Group.query.get_or_404(group_id)
    try:
        data = request.get_json()
        data['group_id'] = group.id  # Associate settlement with group

        # Validate required fields
        required_fields = ['amount', 'payer_id', 'receiver_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
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

@settlements_bp.route("/api/settlements/<int:group_id>", methods=["GET"])
def get_settlements_api(group_id):
    """API endpoint to get recent settlements (ACTUAL PAYMENT HISTORY)"""
    group = Group.query.get_or_404(group_id)
    try:
        limit = request.args.get('limit', 10, type=int)
        settlements = SettlementService.get_recent_settlements(group.id, limit)
        return jsonify({'settlements': settlements}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settlements_bp.route("/settlements", methods=["GET", "POST"])
def manage_settlements():
    """Web page to manage settlements"""
    # Always recalculate balances when page loads
    BalanceService.recalculate_all_balances()
    
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

        # Use service to create settlement (which will recalculate balances)
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
    """Delete settlement and recalculate all balances"""
    success, error = SettlementService.delete_settlement(settlement_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error})

@settlements_bp.route("/edit_settlement/<int:settlement_id>", methods=["POST"])
def edit_settlement(settlement_id):
    """Edit settlement and recalculate all balances"""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    # Use service method which will recalculate all balances
    success, error = SettlementService.update_settlement(settlement_id, data)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 500