from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from models import db, Expense, User, Category   # import db + Expense

app = Flask(__name__)

# PostgreSQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@localhost/expense_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize db with app
db.init_app(app)

@app.route('/manage')
def manage():
    return render_template('manage.html')

@app.route('/')
def home():
    return redirect(url_for('add_expense'))

@app.route('/expenses')
def expenses():
    all_expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = Category.query.all()
    users = User.query.all()
    
    # Convert to safe JSON-serializable lists
    categories_data = [{'id': c.id, 'name': c.name} for c in categories]
    users_data = [{'id': u.id, 'name': u.name} for u in users]
    
    return render_template(
        'expenses.html',
        expenses=all_expenses,
        categories=categories_data,
        users=users_data
    )

# Example: Users
@app.route("/users", methods=["GET", "POST"])
def manage_users():
    error = None
    next_url = request.form.get("next") or request.args.get("next") or url_for("add_expense")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            if User.query.filter_by(name=name).first():
                error = f"User '{name}' already exists"
            else:
                new_user = User(name=name)
                db.session.add(new_user)
                db.session.commit()
                return redirect(next_url)
        # If POST but empty name or error, re-render form
        users = User.query.all()
        return render_template("users.html", users=users, error=error, next_url=next_url)

    # GET request
    users = User.query.all()
    return render_template("users.html", users=users, error=error, next_url=next_url)





@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.expenses:
        error = f"Cannot delete user '{user.name}' because they have existing expenses."
        users = User.query.all()
        return render_template("users.html", users=users, error=error)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("manage_users"))

# Manage Categories
@app.route("/categories", methods=["GET", "POST"])
def manage_categories():
    error = None
    next_url = request.form.get("next") or request.args.get("next") or url_for("add_expense")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            if Category.query.filter_by(name=name).first():
                error = f"Category '{name}' already exists"
            else:
                new_cat = Category(name=name)
                db.session.add(new_cat)
                db.session.commit()
                return redirect(next_url)
        # If POST but empty name or error, re-render form
        categories = Category.query.all()
        return render_template("categories.html", categories=categories, error=error, next_url=next_url)

    # GET request
    categories = Category.query.all()
    return render_template("categories.html", categories=categories, error=error, next_url=next_url)

    

@app.route("/delete_category/<int:cat_id>")
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.expenses:
        error = f"Cannot delete category '{cat.name}' becasue it has existing expenses."
        categories = Category.query.all()
        return render_template("categories.html", categories=categories, error=error)
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for("manage_categories"))

@app.route("/store_suggestions")
def store_suggestions():
    query = request.args.get("q", "").strip()
    if not query:
        return {"suggestions": []}

    # Query the database for matching descriptions
    matches = (
        Expense.query
        .filter(Expense.category_description.ilike(f"%{query}%"))
        .with_entities(Expense.category_description)
        .distinct()
        .limit(10)  # Limit to 10 suggestions
        .all()
    )
    # Flatten the list
    suggestions = [m[0] for m in matches if m[0]]
    return {"suggestions": suggestions}

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    error = None
    users = User.query.all()
    categories = Category.query.all()
    all_expenses = Expense.query.order_by(Expense.date.desc()).all()  # get table data

    users_data = [{'id': u.id, 'name': u.name} for u in users]
    categories_data = [{'id': c.id, 'name': c.name} for c in categories]

    if request.method == 'POST':
        try:
            amount = request.form['amount']
            category_id = request.form.get('category_id')
            user_id = request.form.get('user_id')
            date_str = request.form['date'] or datetime.today().strftime('%Y-%m-%d')
            category_description = request.form.get('category_description', None)

            # Handle Add/Remove Users or Categories redirect
            if user_id == "manage":
                return redirect(url_for("manage_users", next=url_for("add_expense")))
            if category_id == "manage":
                return redirect(url_for("manage_categories", next=url_for("add_expense")))

            # Validate amount
            try:
                amount = float(amount)
                if amount <= 0:
                    error = "Amount must be positive"
            except ValueError:
                error = "Amount must be a number"

            # Validate user
            user = User.query.get(int(user_id)) if user_id else None
            if not user:
                error = "Please select a valid user"

            # Validate category
            category = Category.query.get(int(category_id)) if category_id else None
            if not category:
                error = "Please select a valid category"

            # Validate date
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                error = "Invalid date format. Use YYYY-MM-DD"

            if error:
                return render_template(
                    'add_expense.html',
                    error=error,
                    users=users,
                    categories=categories,
                    expenses=all_expenses  # still pass table data
                )

            # Add expense
            expense = Expense(
                amount=amount,
                user_id=user.id,
                category_id=category.id,
                category_description=category_description if category_description else None,
                date=date
            )
            db.session.add(expense)
            db.session.commit()

            return redirect(url_for('add_expense'))  # redirect back to same page

        except Exception as e:
            error = "An unexpected error occurred: " + str(e)
            return render_template(
                'add_expense.html',
                error=error,
                users=users_data,
                categories=categories_data,
                expenses=all_expenses
            )

    return render_template(
        'add_expense.html',
        error=None,
        users=users_data,
        categories=categories_data,
        expenses=all_expenses
    )



#Delete expenses in the table
@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    try:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(e)
        return jsonify({'success': False, 'error': str(e)})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
