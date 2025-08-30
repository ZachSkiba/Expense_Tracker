from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from models import db, Expense, User, Category, ExpenseParticipant, Balance
from balance_service import BalanceService
# NEW: Import the service
from app.services.expense_service import ExpenseService

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/")
def home():
    # Always recalculate balances when loading home page
    BalanceService.recalculate_all_balances()
    return redirect(url_for("expenses.add_expense"))

@expenses_bp.route("/expenses")
def expenses():
    # Always recalculate balances when loading expenses page
    BalanceService.recalculate_all_balances()
    
    # Use services for all data
    from app.services.user_service import UserService
    from app.services.category_service import CategoryService
    
    all_expenses = ExpenseService.get_all_expenses()
    categories_data = CategoryService.get_all_data()
    users_data = UserService.get_all_data()

    return render_template("expenses.html", 
                         expenses=all_expenses, 
                         categories=categories_data, 
                         users=users_data,
                         show_participants=True)  # Show participants on view all expenses page

@expenses_bp.route("/store_suggestions")
def store_suggestions():
    query = request.args.get("q", "").strip()
    # Use service instead of direct query
    suggestions = ExpenseService.get_store_suggestions(query)
    return {"suggestions": suggestions}

@expenses_bp.route("/add-expense", methods=["GET", "POST"])
def add_expense():
    # Always recalculate balances when loading add expense page
    BalanceService.recalculate_all_balances()
    
    from app.services.user_service import UserService
    from app.services.category_service import CategoryService
    
    error = None
    all_expenses = ExpenseService.get_all_expenses()
    users_data = UserService.get_all_data()
    categories_data = CategoryService.get_all_data()

    if request.method == "POST":
        # Handle manage redirects first
        user_id = request.form.get('user_id')
        selected_category_id = request.form.get('category_id')
        
        if user_id == "manage":
            return redirect(url_for("users.manage_users", next=url_for("expenses.add_expense")))
        if selected_category_id == "manage":
            return redirect(url_for("categories.manage_categories", next=url_for("expenses.add_expense")))

        # Prepare expense data for service
        expense_data = {
            'amount': request.form.get('amount'),
            'payer_id': user_id,
            'participant_ids': request.form.getlist('participant_ids'),
            'category_id': selected_category_id,
            'category_description': request.form.get('category_description'),
            'date': request.form.get('date') or datetime.today().strftime('%Y-%m-%d')
        }

        # Use service to create expense (which will recalculate all balances)
        expense, errors = ExpenseService.create_expense(expense_data)
        
        if expense:
            return redirect(url_for("expenses.add_expense"))
        else:
            # Handle errors
            error = "; ".join(errors)
            return render_template("add_expense.html", 
                                 error=error, 
                                 users=users_data, 
                                 categories=categories_data, 
                                 expenses=all_expenses,
                                 show_participants=False,  # Don't show participants on main page
                                 # Preserve form data
                                 selected_category_id=selected_category_id,
                                 amount=expense_data.get('amount'),
                                 category_description=expense_data.get('category_description'),
                                 date=expense_data.get('date'))

    return render_template("add_expense.html", 
                         error=None, 
                         users=users_data, 
                         categories=categories_data, 
                         expenses=all_expenses,
                         show_participants=False)  # Don't show participants on main page

@expenses_bp.route("/delete_expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    """Delete expense and recalculate all balances"""
    # Use service instead of direct database operations (which will recalculate all balances)
    success, error = ExpenseService.delete_expense(expense_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error})

@expenses_bp.route("/edit_expense/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):
    """Edit expense and recalculate all balances"""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    # Use service instead of direct database operations (which will recalculate all balances)
    success, error = ExpenseService.update_expense(expense_id, data)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 500

@expenses_bp.route("/expense_details/<int:expense_id>")
def expense_details(expense_id):
    """API endpoint to get detailed expense information including participants"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        
        participants_data = []
        for participant in expense.participants:
            participants_data.append({
                'user_id': participant.user_id,
                'user_name': participant.user.name,
                'amount_owed': participant.amount_owed
            })
        
        expense_data = {
            'id': expense.id,
            'amount': expense.amount,
            'category': expense.category_obj.name,
            'description': expense.category_description,
            'payer': expense.user.name,
            'payer_id': expense.user_id,
            'date': expense.date.strftime('%Y-%m-%d'),
            'participants': participants_data
        }
        
        return jsonify({'expense': expense_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500