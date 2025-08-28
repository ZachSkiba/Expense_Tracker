from flask import Blueprint, render_template, request, redirect, url_for
from models import db, User

users_bp = Blueprint("users", __name__)

@users_bp.route("/users", methods=["GET", "POST"])
def manage_users():
    error = None
    next_url = request.form.get("next") or request.args.get("next") or url_for("expenses.add_expense")

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
        users = User.query.all()
        return render_template("users.html", users=users, error=error, next_url=next_url)

    users = User.query.all()
    return render_template("users.html", users=users, error=error, next_url=next_url)


@users_bp.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    error = None

    payer_expenses = user.expenses
    participant_expenses = user.expense_participants
    net_balance = user.get_net_balance()

    details = []
    if payer_expenses:
        details.append(f"{user.name} paid for <a href='{url_for('expenses.add_expense', user_id=user.id)}'>{len(payer_expenses)} expense(s)</a>.")
    if net_balance > 0:
        details.append(
            f"{user.name} is owed <strong>${net_balance:.2f}</strong> "
            f"(<a href='{url_for('balances.balances_page', user_id=user.id)}'>view balance</a>)."
        )
    else:
        details.append(
            f"{user.name} owes <strong>${abs(net_balance):.2f}</strong> "
            f"(<a href='{url_for('balances.balances_page', user_id=user.id)}'>view balance</a>)."
        )

    if details:
        error = (
            f"<span style='color: red; font-weight: bold;'>{user.name} cannot be removed because:</span><br>"
            + "<br>".join(details)
        )
        users = User.query.all()
        return render_template("users.html", users=users, error=error)

    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("users.manage_users"))
