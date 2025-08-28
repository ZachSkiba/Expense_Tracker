from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Category

categories_bp = Blueprint("categories", __name__)

@categories_bp.route("/categories", methods=["GET", "POST"])
def manage_categories():
    error = None
    next_url = request.form.get("next") or request.args.get("next") or url_for("expenses.add_expense")

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
        categories = Category.query.all()
        return render_template("categories.html", categories=categories, error=error, next_url=next_url)

    categories = Category.query.all()
    return render_template("categories.html", categories=categories, error=error, next_url=next_url)

@categories_bp.route("/delete_category/<int:cat_id>")
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.expenses:
        error = f"Cannot delete category '{cat.name}' because it has existing expenses."
        categories = Category.query.all()
        return render_template("categories.html", categories=categories, error=error)
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for("categories.manage_categories"))
