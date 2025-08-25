from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from models import db, Expense   # import db + Expense

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
    return render_template('expenses.html', expenses=all_expenses)

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    error = None
    categories = ['Food', 'Transport', 'Entertainment', 'Bills', 'Shopping', 'Other']

    if request.method == 'POST':
        try:
            # Get form data
            amount = request.form['amount']
            category = request.form['category']
            custom_category = request.form.get('custom_category', '').strip()
            paid_by = request.form['paid_by'].strip()
            date_str = request.form['date'] or datetime.today().strftime('%Y-%m-%d')

            # Validate amount
            try:
                amount = float(amount)
                if amount <= 0:
                    error = "Amount must be positive"
            except ValueError:
                error = "Amount must be a number"

            # Handle "Other" category
            if category == 'Other':
                if not custom_category:
                    error = "Please enter a category for 'Other'"
                else:
                    category = custom_category

            # Validate category and paid_by
            if category not in categories and category != custom_category:
                error = "Invalid category selected"
            if not paid_by:
                error = "Paid By field cannot be empty"

            # Validate date
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                error = "Invalid date format. Use YYYY-MM-DD"

            if error:
                return render_template('add_expense.html',
                                       error=error,
                                       amount=request.form['amount'],
                                       category=request.form['category'],
                                       custom_category=custom_category,
                                       paid_by=paid_by,
                                       date=request.form['date'],
                                       categories=categories)

            # Add expense to DB
            expense = Expense(amount=amount, category=category,
                              paid_by=paid_by, date=date)
            db.session.add(expense)
            db.session.commit()

            return redirect(url_for('expenses'))

        except Exception as e:
            error = "An unexpected error occurred: " + str(e)
            return render_template('add_expense.html', error=error, categories=categories)

    return render_template('add_expense.html', error=None, categories=categories)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
