# Add these imports to your balances.py file if not already present
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from balance_service import BalanceService
from app.services.settlement_service import SettlementService
from app.services.user_service import UserService
from models import db, User, Category
from datetime import datetime

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
    """API endpoint to get current balances - READ ONLY, no recalculation"""
    try:
        # Get balances WITHOUT recalculating (balances are calculated when data changes)
        balances = BalanceService.get_all_balances()
        return jsonify({'balances': balances}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@balances_bp.route("/api/settlement-suggestions", methods=["GET"])
def get_settlement_suggestions_api():
    """API endpoint to get settlement suggestions (who should pay whom) - READ ONLY"""
    try:
        # Get suggestions WITHOUT recalculating (based on current balances)
        suggestions = BalanceService.get_settlement_suggestions()
        return jsonify({'suggestions': suggestions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@balances_bp.route("/api/settlements", methods=["GET"])
def get_settlements_api():
    """API endpoint to get all settlements/payments data"""
    try:
        settlements = SettlementService.get_settlement_data()
        return jsonify({'settlements': settlements}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

    
@balances_bp.route("/balances-settlements", methods=["GET", "POST"])
def combined_balances_settlements():
    """Combined balances and settlements management page"""
    # Always recalculate balances when page loads
    BalanceService.recalculate_all_balances()
    
    error = None
    users_data = UserService.get_all_data()
    
    # Handle settlement form submission
    if request.method == "POST":
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
            return redirect(url_for("balances.combined_balances_settlements"))
        else:
            # Handle errors
            error = "; ".join(errors)
            # Continue to render page with error and preserved form data
    
    # Get current balances
    balances = BalanceService.get_all_balances()
    
    # Get settlement suggestions
    settlements = BalanceService.get_settlement_suggestions()
    
    # Get recent settlements for the payments history table
    settlements_data = SettlementService.get_settlement_data()
    
    return render_template("combined_balances_settlements.html", 
                         error=error,
                         users=users_data,
                         balances=balances,
                         settlements=settlements,  # Settlement suggestions
                         settlements_data=settlements_data,  # Actual payment history
                         # Preserve form data on error
                         amount=request.form.get('amount') if error else None,
                         payer_id=request.form.get('payer_id') if error else None,
                         receiver_id=request.form.get('receiver_id') if error else None,
                         description=request.form.get('description') if error else None,
                         date=request.form.get('date') if error else None)