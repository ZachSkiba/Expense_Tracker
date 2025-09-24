# app/routes/settlements.py - UPDATED with group filtering

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app.services.tracker.settlement_service import SettlementService
from app.services.tracker.user_service import UserService
from models import Group, db, Settlement, User
from app.services.tracker.balance_service import BalanceService
from datetime import datetime
from flask_login import current_user, login_required, login_user

settlements_bp = Blueprint("settlements", __name__)

@settlements_bp.route("/api/settlements/<int:group_id>", methods=["POST"])
def add_settlement_api(group_id):
    """API endpoint to add new settlement - group-aware"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        data['group_id'] = group_id  # Ensure group context

        # Validate required fields
        required_fields = ['amount', 'payer_id', 'receiver_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify users are group members
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

@settlements_bp.route("/api/settlements/<int:group_id>", methods=["GET"])
def get_settlements_api(group_id):
    """API endpoint to get recent settlements for a group"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Get group-specific settlements
        settlements = Settlement.query.filter_by(group_id=group_id)\
            .order_by(Settlement.date.desc()).limit(limit).all()
        
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
        
        return jsonify({'settlements': settlements_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Keep legacy routes but make them group-aware where possible
@settlements_bp.route("/settlements", methods=["GET", "POST"])
def manage_settlements():
    """Web page to manage settlements - legacy route"""
    # This is a legacy route - redirect to dashboard for group selection
    flash('Please select a tracker from your dashboard to manage settlements', 'info')
    return redirect(url_for('dashboard.home'))

@settlements_bp.route("/delete_settlement/<int:settlement_id>", methods=["POST"])
def delete_settlement(settlement_id):
    """Delete settlement and recalculate balances - group-aware"""
    settlement = Settlement.query.get_or_404(settlement_id)
    
    # Check user access
    if settlement.group_id:
        group = Group.query.get(settlement.group_id)
        if not group or current_user not in group.members:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    success, error = SettlementService.delete_settlement(settlement_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error})

@settlements_bp.route("/edit_settlement/<int:settlement_id>", methods=["POST"])
def edit_settlement(settlement_id):
    """Edit settlement and recalculate balances - group-aware"""
    settlement = Settlement.query.get_or_404(settlement_id)
    
    # Check user access
    if settlement.group_id:
        group = Group.query.get(settlement.group_id)
        if not group or current_user not in group.members:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    # Use service method which will recalculate balances
    success, error = SettlementService.update_settlement(settlement_id, data)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 500