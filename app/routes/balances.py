from flask import Blueprint, request, jsonify, render_template
from balance_service import BalanceService
from models import db, User, Category

balances_bp = Blueprint("balances", __name__)

@balances_bp.route("/api/expenses", methods=["POST"])
def add_expense_api():
    """API endpoint to add new expense with participants"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'payer_id', 'participant_ids', 'category_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create expense (which will recalculate all balances)
        expense = BalanceService.create_expense_with_participants(
            amount=float(data['amount']),
            payer_id=int(data['payer_id']),
            participant_ids=data['participant_ids'],
            category_id=int(data['category_id']),
            category_description=data.get('category_description'),
            date=data.get('date'),
            split_type=data.get('split_type', 'equal')
        )
        
        if expense:
            return jsonify({
                'success': True,
                'expense_id': expense.id,
                'message': 'Expense added successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to create expense'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@balances_bp.route("/api/balances", methods=["GET"])
def get_balances_api():
    """API endpoint to get current balances"""
    try:
        # Always recalculate balances to ensure accuracy
        BalanceService.recalculate_all_balances()
        balances = BalanceService.get_all_balances()
        return jsonify({'balances': balances}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@balances_bp.route("/api/settlements", methods=["GET"])
def get_settlements_api():
    """API endpoint to get settlement suggestions"""
    try:
        # Always recalculate balances first to ensure accuracy
        BalanceService.recalculate_all_balances()
        settlements = BalanceService.get_settlement_suggestions()
        return jsonify({'settlements': settlements}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@balances_bp.route("/balances", methods=["GET"])
def balances_page():
    """Web page to view balances"""
    # Recalculate balances every time the page is loaded
    BalanceService.recalculate_all_balances()
    balances = BalanceService.get_all_balances()
    settlements = BalanceService.get_settlement_suggestions()
    
    return render_template("balances.html", balances=balances, settlements=settlements)

@balances_bp.route("/api/balances/recalculate", methods=["POST"])
def recalculate_balances():
    """Recalculate all balances from expenses and settlements (admin function)"""
    try:
        success = BalanceService.recalculate_all_balances()
        if success:
            return jsonify({'message': 'Balances recalculated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to recalculate balances'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500