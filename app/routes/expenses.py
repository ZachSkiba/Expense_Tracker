from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from models import db, Expense, User, Category

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

            if user_id == "manage":
                return redirect(url_for("users.manage_users", next=url_for("expenses.add_expense")))
            if selected_category_id == "manage":
                return redirect(url_for("categories.manage_categories", next=url_for("expenses.add_expense")))

            try:
                amount = float(amount)
                if amount <= 0:
                    error = "Amount must be positive"
            except ValueError:
                error = "Amount must be a number"

            user = User.query.get(int(user_id)) if user_id else None
            if not user:
                error = "Please select a valid user"

            category = Category.query.get(int(selected_category_id)) if selected_category_id else None
            if not category:
                error = "Please select a valid category"

            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                error = "Invalid date format. Use YYYY-MM-DD"

            if error:
                return render_template("add_expense.html", error=error, users=users, categories=categories, expenses=all_expenses, selected_category_id=selected_category_id)

            expense = Expense(amount=amount, user_id=user.id, category_id=category.id, category_description=category_description, date=date)
            db.session.add(expense)
            db.session.commit()
            return redirect(url_for("expenses.add_expense"))

        except Exception as e:
            error = f"Unexpected error: {e}"
            return render_template("add_expense.html", error=error, users=users_data, categories=categories_data, expenses=all_expenses, selected_category_id=selected_category_id)

    return render_template("add_expense.html", error=None, users=users_data, categories=categories_data, expenses=all_expenses)

@expenses_bp.route("/delete_expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    try:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@expenses_bp.route("/edit_expense/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    try:
        # Update fields if they exist in the received data
        if 'amount' in data:
            expense.amount = float(data['amount'])
        if 'description' in data:
            expense.category_description = data['description']
        if 'date' in data:
            expense.date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Handle category and user by looking them up by name
        if 'category' in data:
            category = Category.query.filter_by(name=data['category']).first()
            if category:
                expense.category_id = category.id
            else:
                return jsonify({'success': False, 'error': f"Category '{data['category']}' not found"}), 400
        
        if 'user' in data:
            user = User.query.filter_by(name=data['user']).first()
            if user:
                expense.user_id = user.id
            else:
                return jsonify({'success': False, 'error': f"User '{data['user']}' not found"}), 400

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500