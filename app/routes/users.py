from flask import Blueprint, render_template, request, redirect, url_for
from models import db, User
# NEW: Import the service
from app.services.user_service import UserService

users_bp = Blueprint("users", __name__)

@users_bp.route("/users", methods=["GET", "POST"])
def manage_users():
    error = None
    next_url = request.form.get("next") or request.args.get("next") or url_for("expenses.add_expense")

    if request.method == "POST":
        name = request.form.get("name", "")
        if name:
            # Use service instead of direct database operations
            user, error = UserService.create_user(name)
            if user:
                return redirect(next_url)
            # If there's an error, it will be displayed below
        
        # Get users using service
        users = UserService.get_all()
        return render_template("users.html", users=users, error=error, next_url=next_url)

    # Get users using service
    users = UserService.get_all()
    return render_template("users.html", users=users, error=error, next_url=next_url)

@users_bp.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    # Use service to check if user can be deleted
    can_delete, reasons = UserService.can_delete_user(user_id)
    
    if not can_delete:
        user = User.query.get_or_404(user_id)  # We still need this for the user name
        error = (
            f"<span style='color: red; font-weight: bold;'>{user.name} cannot be removed because:</span><br>"
            + "<br>".join(reasons)
        )
        users = UserService.get_all()
        return render_template("users.html", users=users, error=error)
    
    # Use service to delete user
    success, error = UserService.delete_user(user_id)
    if not success:
        users = UserService.get_all()
        return render_template("users.html", users=users, error=error)
    
    return redirect(url_for("users.manage_users"))