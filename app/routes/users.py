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
    if user.expenses:
        error = f"Cannot delete user '{user.name}' because they have existing expenses."
        users = User.query.all()
        return render_template("users.html", users=users, error=error)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("users.manage_users"))
