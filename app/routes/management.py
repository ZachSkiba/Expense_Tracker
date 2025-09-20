# app/routes/management.py - UPDATE to be group-aware

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Category, Group
from app.services.user_service import UserService
from app.services.category_service import CategoryService

management_bp = Blueprint("management", __name__)

@management_bp.route("/manage/<int:group_id>", methods=["GET", "POST"])
@login_required
def manage_data(group_id):
    """Group-aware user and category management"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    error = None
    success = None
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_user":
            # For groups, we don't add users directly - they join via invite codes
            flash('Users must join this group using the invite code', 'info')
            
        elif action == "add_category":
            name = request.form.get("category_name", "").strip()
            if name:
                # Check if category already exists in this group
                existing = Category.query.filter_by(name=name, group_id=group_id).first()
                if existing:
                    flash(f"Category '{name}' already exists in this group", 'error')
                else:
                    try:
                        # Create group-specific category
                        category = Category(name=name, group_id=group_id)
                        db.session.add(category)
                        db.session.commit()
                        flash(f"Category '{name}' added successfully!", 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f"Error adding category: {str(e)}", 'error')
    
    # Get group-specific data
    users = list(group.members)  # Only group members
    categories = Category.query.filter_by(group_id=group_id).all()  # Only group categories
    
    next_url = request.args.get('next', url_for('expenses.group_tracker', group_id=group_id))
    
    return render_template("management.html", 
                         users=users, 
                         categories=categories,
                         group=group,
                         error=error,
                         success=success,
                         next_url=next_url)

@management_bp.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    """Delete user - but for groups, this removes them from the group"""
    # Get group_id from referrer or form
    group_id = request.args.get('group_id', type=int)
    if not group_id:
        flash('Group context required', 'error')
        return redirect(url_for('dashboard.home'))
    
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    
    # Check if current user can manage this group
    if not current_user.is_group_admin(group):
        flash('Only group admins can manage users', 'error')
        return redirect(url_for('management.manage_data', group_id=group_id))
    
    if user == group.creator:
        flash('Cannot remove the group creator', 'error')
    else:
        try:
            group.remove_member(user)
            db.session.commit()
            flash(f"Removed {user.name} from the group", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error removing user: {str(e)}", 'error')
    
    return redirect(url_for('management.manage_data', group_id=group_id))

@management_bp.route("/delete_category/<int:cat_id>")
@login_required
def delete_category(cat_id):
    """Delete category from group"""
    category = Category.query.get_or_404(cat_id)
    group_id = category.group_id
    
    if not group_id:
        flash('Cannot delete system categories', 'error')
        return redirect(url_for('dashboard.home'))
    
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard.home'))
    
    # Check if category has expenses
    if category.expenses:
        flash(f"Cannot delete category '{category.name}' because it has existing expenses.", 'error')
    else:
        try:
            db.session.delete(category)
            db.session.commit()
            flash(f"Category '{category.name}' deleted successfully!", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting category: {str(e)}", 'error')
    
    return redirect(url_for('management.manage_data', group_id=group_id))