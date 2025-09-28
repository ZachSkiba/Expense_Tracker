# app/routes/tracker/management.py - UPDATED with income categories management

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Category, Group, Expense, Balance, ExpenseParticipant, Settlement, RecurringPayment, user_groups
from models.income_models import IncomeCategory, IncomeEntry
from app.services.tracker.user_service import UserService
from app.services.tracker.category_service import CategoryService
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
        
        elif action == "add_income_category":
            name = request.form.get("income_category_name", "").strip()
            if name:
                # Check if income category already exists in this group
                existing = IncomeCategory.query.filter_by(name=name, group_id=group_id).first()
                if existing:
                    flash(f"Income category '{name}' already exists in this group", 'error')
                else:
                    try:
                        # Create group-specific income category
                        income_category = IncomeCategory(name=name, group_id=group_id)
                        db.session.add(income_category)
                        db.session.commit()
                        flash(f"Income category '{name}' added successfully!", 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f"Error adding income category: {str(e)}", 'error')
    
    # Get group-specific data
    users = list(group.members)  # Only group members
    categories = Category.query.filter_by(group_id=group_id).all()  # Only group categories
    income_categories = IncomeCategory.query.filter_by(group_id=group_id).all()  # Only group income categories
    
    next_url = request.args.get('next', url_for('expenses.group_tracker', group_id=group_id))

    return render_template("tracker/management.html", 
                         users=users, 
                         categories=categories,
                         income_categories=income_categories,
                         group=group,
                         error=error,
                         success=success,
                         next_url=next_url)

@management_bp.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    """Delete user - removes from group and deletes from DB if it's their only group"""
    group_id = request.args.get('group_id', type=int)
    if not group_id:
        flash('Group context required', 'error')
        return redirect(url_for('dashboard.home'))
    
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    
    if not current_user.is_group_admin(group):
        flash('Only group admins can manage users', 'error')
        return redirect(url_for('management.manage_data', group_id=group_id))
    
    if user == group.creator:
        flash('Cannot remove the group creator', 'error')
        return redirect(url_for('management.manage_data', group_id=group_id))
    
    # Check if user can be removed from the group
    can_remove, reasons = _can_remove_user_from_group(user, group)
    
    if not can_remove:
        # Format the detailed error message.
        error_message = f"<strong>{user.name} cannot be removed because:</strong><br>"
        error_message += "<br>".join(reasons)
        
        # Gather all the data needed to render the management page again.
        users = list(group.members)
        categories = Category.query.filter_by(group_id=group_id).all()
        income_categories = IncomeCategory.query.filter_by(group_id=group_id).all()
        next_url = url_for('expenses.group_tracker', group_id=group_id)
        
        # Render the template directly, passing the error message.
        return render_template("tracker/management.html",
                               group=group,
                               users=users,
                               categories=categories,
                               income_categories=income_categories,
                               error=error_message,  # Pass the error here
                               success=None,
                               next_url=next_url)
    else:
        try:
            is_placeholder_user = user.email.endswith('.local')
            user_group_count = len(user.groups)
            user_name = user.name
            
            if user not in group.members:
                flash(f"{user_name} is not a member of this group", 'warning')
                return redirect(url_for('management.manage_data', group_id=group_id))
            
            if is_placeholder_user and user_group_count <= 1 and _can_safely_delete_placeholder_user(user, group_id):
                user_id_to_delete = user.id
                
                # Delete income entries
                IncomeEntry.query.filter_by(user_id=user_id_to_delete, group_id=group_id).delete(synchronize_session=False)
                
                ExpenseParticipant.query.filter_by(user_id=user_id_to_delete, group_id=group_id).delete(synchronize_session=False)
                Expense.query.filter_by(user_id=user_id_to_delete, group_id=group_id).delete(synchronize_session=False)
                RecurringPayment.query.filter_by(user_id=user_id_to_delete, group_id=group_id).delete(synchronize_session=False)
                Balance.query.filter_by(user_id=user_id_to_delete, group_id=group_id).delete(synchronize_session=False)
                Settlement.query.filter(
                    Settlement.group_id == group_id,
                    db.or_(Settlement.payer_id == user_id_to_delete, Settlement.receiver_id == user_id_to_delete)
                ).delete(synchronize_session=False)

                if user in group.members:
                    group.members.remove(user)

                db.session.delete(user)
                db.session.commit()
                flash(f"Removed and completely deleted placeholder user '{user_name}'.", 'success')
            else:
                # For regular users or placeholders with data in other groups, just remove them.
                group.remove_member(user)
                db.session.commit()
                flash(f"Removed '{user_name}' from the group.", 'success')
                
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
    
    # Check if user has non-zero balance in this group
    balance = Balance.query.filter_by(user_id=user.id, group_id=group.id).first()
    if balance and abs(balance.amount) > 0.01:  # Not zero (accounting for floating point)
        balance_url = url_for('expenses.group_tracker', group_id=group.id)
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

def _can_safely_delete_placeholder_user(user, current_group_id):
    """
    Check if a placeholder user can be safely deleted from the database
    This ensures they have no financial data outside the current group
    """
    # Check for expenses outside this group
    other_expenses = Expense.query.filter(
        Expense.user_id == user.id,
        Expense.group_id != current_group_id
    ).count()
    
    if other_expenses > 0:
        return False
    
    # Check for income entries outside this group
    other_income = IncomeEntry.query.filter(
        IncomeEntry.user_id == user.id,
        IncomeEntry.group_id != current_group_id
    ).count()
    
    if other_income > 0:
        return False
    
    # Check for balances outside this group
    other_balances = Balance.query.filter(
        Balance.user_id == user.id,
        Balance.group_id != current_group_id,
        Balance.amount != 0
    ).count()
    
    if other_balances > 0:
        return False
    
    # Check for settlements outside this group
    other_settlements = db.session.query(func.count()).filter(
        db.or_(
            db.and_(Settlement.payer_id == user.id, Settlement.group_id != current_group_id),
            db.and_(Settlement.receiver_id == user.id, Settlement.group_id != current_group_id)
        )
    ).scalar()
    
    if other_settlements > 0:
        return False
    
    # Check for recurring payments outside this group
    other_recurring = RecurringPayment.query.filter(
        RecurringPayment.user_id == user.id,
        RecurringPayment.group_id != current_group_id
    ).count()
    
    if other_recurring > 0:
        return False
    
    return True

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

@management_bp.route("/delete_income_category/<int:income_cat_id>")
@login_required
def delete_income_category(income_cat_id):
    """Delete income category from group"""
    income_category = IncomeCategory.query.get_or_404(income_cat_id)
    group_id = income_category.group_id
    
    if not group_id:
        flash('Cannot delete system income categories', 'error')
        return redirect(url_for('dashboard.home'))
    
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard.home'))
    
    # Check if income category has income entries
    if income_category.income_entries:
        flash(f"Cannot delete income category '{income_category.name}' because it has existing income entries.", 'error')
    else:
        try:
            db.session.delete(income_category)
            db.session.commit()
            flash(f"Income category '{income_category.name}' deleted successfully!", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting income category: {str(e)}", 'error')
    
    return redirect(url_for('management.manage_data', group_id=group_id))