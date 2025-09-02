from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.user_service import UserService
from app.services.category_service import CategoryService

management_bp = Blueprint("management", __name__)

@management_bp.route("/management", methods=["GET", "POST"])
def manage_data():
    error = None
    success = None
    next_url = request.form.get("next") or request.args.get("next") or url_for("expenses.add_expense")

    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_user":
            name = request.form.get("user_name", "")
            if name:
                user, error = UserService.create_user(name)
                if user:
                    success = f"User '{user.name}' added successfully!"
                    
        elif action == "add_category":
            name = request.form.get("category_name", "")
            if name:
                category, error = CategoryService.create_category(name)
                if category:
                    success = f"Category '{category.name}' added successfully!"

    # Always get fresh data
    users = UserService.get_all()
    categories = CategoryService.get_all()
    
    return render_template("management.html", 
                         users=users, 
                         categories=categories, 
                         error=error, 
                         success=success,
                         next_url=next_url)

@management_bp.route("/management/delete_user/<int:user_id>")
def delete_user(user_id):
    # Use service to check if user can be deleted
    can_delete, reasons = UserService.can_delete_user(user_id)
    
    if not can_delete:
        from models import User
        user = User.query.get_or_404(user_id)
        error = (
            f"<span style='color: red; font-weight: bold;'>{user.name} cannot be removed because:</span><br>"
            + "<br>".join(reasons)
        )
        users = UserService.get_all()
        categories = CategoryService.get_all()
        return render_template("management.html", users=users, categories=categories, error=error)
    
    # Use service to delete user
    success, error = UserService.delete_user(user_id)
    if success:
        flash("User deleted successfully!", "success")
    else:
        flash(f"Error deleting user: {error}", "error")
    
    return redirect(url_for("management.manage_data"))

@management_bp.route("/management/delete_category/<int:cat_id>")
def delete_category(cat_id):
    # Use service to check if category can be deleted
    can_delete, error_message = CategoryService.can_delete_category(cat_id)
    
    if not can_delete:
        users = UserService.get_all()
        categories = CategoryService.get_all()
        return render_template("management.html", users=users, categories=categories, error=error_message)
    
    # Use service to delete category
    success, error = CategoryService.delete_category(cat_id)
    if success:
        flash("Category deleted successfully!", "success")
    else:
        flash(f"Error deleting category: {error}", "error")
    
    return redirect(url_for("management.manage_data"))
