# app/routes/management.py - UPDATE to be group-aware with direct user creation

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Category, Group, Expense, Balance
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from sqlalchemy import func
from datetime import datetime

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
            name = request.form.get("user_name", "").strip()
            if name:
                # Check if someone with this name is already in this specific group
                existing_in_group = None
                for member in group.members:
                    if member.name == name:
                        existing_in_group = member
                        break
                
                if existing_in_group:
                    flash(f"User '{name}' is already a member of this group", 'error')
                else:
                    # Always create new user (even if display name exists elsewhere)
                    try:
                        # Create placeholder email for tracking users
                        placeholder_email = f"placeholder_{group_id}_{name.lower().replace(' ', '_')}_{datetime.utcnow().timestamp()}@tracker.local"
                        
                        new_user = User(
                            full_name=name,
                            display_name=name,
                            email=placeholder_email,
                            is_active=True
                        )
                        db.session.add(new_user)
                        db.session.flush()  # Get the user ID
                        
                        # Add to group
                        group.add_member(new_user)
                        db.session.commit()
                        flash(f"Added '{name}' to the group", 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f"Error creating user: {str(e)}", 'error')
            else:
                flash("Please enter a user name", 'error')
                
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
    """Delete user - but for groups, this removes them from the group or checks constraints"""
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
        return redirect(url_for('management.manage_data', group_id=group_id))
    
    # Check if user can be removed from the group
    can_remove, reasons = _can_remove_user_from_group(user, group)
    
    if not can_remove:
        # Format the detailed error message
        error_message = f"<strong>{user.name} cannot be removed because:</strong><br>"
        error_message += "<br>".join(reasons)
        flash(error_message, 'error')
    else:
        try:
            group.remove_member(user)
            db.session.commit()
            flash(f"Removed {user.name} from the group", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error removing user: {str(e)}", 'error')
    
    return redirect(url_for('management.manage_data', group_id=group_id))

def _can_remove_user_from_group(user, group):
    """
    Check if a user can be removed from a group
    Returns: (can_remove_boolean, list_of_reasons)
    """
    reasons = []
    
    # Check if user has expenses as payer in this group
    payer_expenses = Expense.query.filter_by(user_id=user.id, group_id=group.id).all()
    if payer_expenses:
        expense_url = url_for('expenses.group_tracker', group_id=group.id)
        reasons.append(
            f"{user.name} paid for "
            f"<a href='{expense_url}'>{len(payer_expenses)} expense(s)</a>"
        )
    
    # Check if user participated in expenses in this group
    from models import ExpenseParticipant
    participant_expenses = db.session.query(ExpenseParticipant)\
        .join(Expense)\
        .filter(ExpenseParticipant.user_id == user.id, Expense.group_id == group.id)\
        .all()
    
    if participant_expenses:
        expense_url = url_for('expenses.group_tracker', group_id=group.id)
        reasons.append(
            f"{user.name} participated in "
            f"<a href='{expense_url}'>{len(participant_expenses)} expense(s)</a>"
        )
    
    # Check if user has non-zero balance in this group
    balance = Balance.query.filter_by(user_id=user.id, group_id=group.id).first()
    if balance and abs(balance.amount) > 0.01:  # Not zero (accounting for floating point)
        balance_url = url_for('expenses.group_tracker', group_id=group.id)  # You might want a dedicated balance view
        if balance.amount > 0:
            reasons.append(
                f"{user.name} is owed <strong>${balance.amount:.2f}</strong> "
                f"(<a href='{balance_url}'>view balances</a>)"
            )
        else:
            reasons.append(
                f"{user.name} owes <strong>${abs(balance.amount):.2f}</strong> "
                f"(<a href='{balance_url}'>view balances</a>)"
            )
    
    can_remove = len(reasons) == 0
    return can_remove, reasons

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