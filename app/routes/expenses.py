from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from models import db, Expense, User, Category, ExpenseParticipant, Balance
from balance_service import BalanceService

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/")
def home():
    return redirect(url_for("expenses.add_expense"))

@expenses_bp.route("/expenses")
def expenses():
    all_expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = Category.query.all()
    users = User.query.all()
    categories_data = [{'id': c.id, 'name': c.name} for c in categories]
    users_data = [{'id': u.id, 'name': u.name} for u in users]

    return render_template("expenses.html", expenses=all_expenses, categories=categories_data, users=users_data)

@expenses_bp.route("/store_suggestions")
def store_suggestions():
    query = request.args.get("q", "").strip()
    if not query:
        return {"suggestions": []}

    matches = (
        Expense.query
        .filter(Expense.category_description.ilike(f"%{query}%"))
        .with_entities(Expense.category_description)
        .distinct()
        .limit(10)
        .all()
    )
    suggestions = [m[0] for m in matches if m[0]]
    return {"suggestions": suggestions}

@expenses_bp.route("/add-expense", methods=["GET", "POST"])
def add_expense():
    error = None
    users = User.query.all()
    categories = Category.query.all()
    all_expenses = Expense.query.order_by(Expense.date.desc()).all()

    users_data = [{'id': u.id, 'name': u.name} for u in users]
    categories_data = [{'id': c.id, 'name': c.name} for c in categories]

    if request.method == "POST":
        try:
            amount = request.form['amount']
            selected_category_id = request.form.get('category_id')
            user_id = request.form.get('user_id')
            date_str = request.form['date'] or datetime.today().strftime('%Y-%m-%d')
            category_description = request.form.get('category_description', None)
            
            # NEW: Get participant IDs
            participant_ids = request.form.getlist('participant_ids')

            if user_id == "manage":
                return redirect(url_for("users.manage_users", next=url_for("expenses.add_expense")))
            if selected_category_id == "manage":
                return redirect(url_for("categories.manage_categories", next=url_for("expenses.add_expense")))

            # Validation
            try:
                amount = float(amount)
                if amount <= 0:
                    error = "Amount must be positive"
            except ValueError:
                error = "Amount must be a number"

            if not user_id or user_id == "manage":
                error = "Please select a valid user"

            if not selected_category_id or selected_category_id == "manage":
                error = "Please select a valid category"

            if not participant_ids:
                error = "Please select at least one participant"

            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                error = "Invalid date format. Use YYYY-MM-DD"

            if error:
                return render_template("add_expense.html", 
                                     error=error, 
                                     users=users_data, 
                                     categories=categories_data, 
                                     expenses=all_expenses, 
                                     selected_category_id=selected_category_id,
                                     amount=amount if 'amount' in locals() else None,
                                     category_description=category_description,
                                     date=date_str)

            # Convert participant IDs to integers
            participant_ids = [int(pid) for pid in participant_ids]

            # Use BalanceService to create expense with participants
            expense = BalanceService.create_expense_with_participants(
                amount=amount,
                payer_id=int(user_id),
                participant_ids=participant_ids,
                category_id=int(selected_category_id),
                category_description=category_description,
                date=date
            )

            if expense:
                return redirect(url_for("expenses.add_expense"))
            else:
                error = "Failed to create expense. Please try again."
                return render_template("add_expense.html", 
                                     error=error, 
                                     users=users_data, 
                                     categories=categories_data, 
                                     expenses=all_expenses)

        except Exception as e:
            error = f"Unexpected error: {e}"
            return render_template("add_expense.html", 
                                 error=error, 
                                 users=users_data, 
                                 categories=categories_data, 
                                 expenses=all_expenses)

    return render_template("add_expense.html", 
                         error=None, 
                         users=users_data, 
                         categories=categories_data, 
                         expenses=all_expenses)

@expenses_bp.route("/delete_expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    """Delete expense and reverse balance changes"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        
        # Get participants before deletion
        participants = expense.participants
        payer_id = expense.user_id
        total_amount = expense.amount
        
        # Calculate what balances need to be reversed
        participant_amounts = {p.user_id: p.amount_owed for p in participants}
        
        # Reverse the balance changes
        # Debit the payer (opposite of original credit)
        BalanceService._update_user_balance(payer_id, -total_amount)
        
        # Credit each participant their share (opposite of original debit)
        for participant_id, amount_owed in participant_amounts.items():
            BalanceService._update_user_balance(participant_id, amount_owed)
        
        # Delete the expense (participants will be deleted via cascade)
        db.session.delete(expense)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@expenses_bp.route("/edit_expense/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):
    """Edit expense and recalculate balances as needed"""
    expense = Expense.query.get_or_404(expense_id)
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    try:
        # Step 1: Reverse old balances BEFORE updating anything
        BalanceService.reverse_balances_for_expense(expense)

        # Step 2: Update expense fields
        if 'amount' in data:
            expense.amount = float(data['amount'])
        if 'category' in data:
            category = Category.query.filter_by(name=data['category']).first()
            if category:
                expense.category_id = category.id
        if 'user' in data:
            user = User.query.filter_by(name=data['user']).first()
            if user:
                expense.user_id = user.id
        if 'description' in data:
            expense.category_description = data['description']
        if 'date' in data:
            expense.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        
        # Step 3: Handle participants if provided
        if 'participants' in data:
            # Remove old participants
            for p in expense.participants:
                db.session.delete(p)
            db.session.flush()  # Ensure deletion is processed
            
            # Add new participants with correct amounts
            participant_count = len(data['participants'])
            if participant_count > 0:
                individual_share = expense.amount / participant_count
                for user_id in data['participants']:
                    participant = ExpenseParticipant(
                        expense_id=expense.id, 
                        user_id=user_id, 
                        amount_owed=individual_share
                    )
                    db.session.add(participant)
        else:
            # If participants weren't updated, recalculate their amounts based on new expense amount
            participant_count = len(expense.participants)
            if participant_count > 0:
                individual_share = expense.amount / participant_count
                for participant in expense.participants:
                    participant.amount_owed = individual_share

        # Step 4: Commit the expense and participant changes
        db.session.commit()

        # Step 5: Apply new balances AFTER all updates are committed
        # Refresh the expense to get updated participants
        db.session.refresh(expense)
        participant_amounts = {p.user_id: p.amount_owed for p in expense.participants}
        
        BalanceService._update_balances_for_expense(
            expense.id,
            expense.user_id,
            participant_amounts
        )
        
        # Final commit for balance changes
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

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