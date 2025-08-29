from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Category
# NEW: Import the service
from app.services.category_service import CategoryService

categories_bp = Blueprint("categories", __name__)

@categories_bp.route("/categories", methods=["GET", "POST"])
def manage_categories():
    error = None
    next_url = request.form.get("next") or request.args.get("next") or url_for("expenses.add_expense")

    if request.method == "POST":
        name = request.form.get("name", "")
        if name:
            # Use service instead of direct database operations
            category, error = CategoryService.create_category(name)
            if category:
                return redirect(next_url)
            # If there's an error, it will be displayed below
            
        # Get categories using service
        categories = CategoryService.get_all()
        return render_template("categories.html", categories=categories, error=error, next_url=next_url)

    # Get categories using service
    categories = CategoryService.get_all()
    return render_template("categories.html", categories=categories, error=error, next_url=next_url)

@categories_bp.route("/delete_category/<int:cat_id>")
def delete_category(cat_id):
    # Use service to check if category can be deleted
    can_delete, error_message = CategoryService.can_delete_category(cat_id)
    
    if not can_delete:
        categories = CategoryService.get_all()
        return render_template("categories.html", categories=categories, error=error_message)
    
    # Use service to delete category
    success, error = CategoryService.delete_category(cat_id)
    if not success:
        categories = CategoryService.get_all()
        return render_template("categories.html", categories=categories, error=error)
    
    return redirect(url_for("categories.manage_categories"))