# app/routes/expenses.py - UPDATED for group-based expense tracking

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime

from sqlalchemy import desc
from models import db, Expense, User, Category, ExpenseParticipant, Balance, Group
from app.services.expense_service import ExpenseService
from app.services.user_service import UserService
from app.services.category_service import CategoryService

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/")
@login_required
def home():
    """Redirect to dashboard - legacy route"""
    return redirect(url_for("dashboard.home"))

@expenses_bp.route("/expenses")
@login_required
def expenses():
    """Legacy route - redirect to dashboard"""
    return redirect(url_for("dashboard.home"))

# Group-specific expense routes
@expenses_bp.route("/group/<int:group_id>/expenses")
@login_required
def group_expenses(group_id):
    """View all expenses for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    # Get group expenses
    expenses = Expense.query.filter_by(group_id=group_id)\
        .order_by(Expense.date.desc()).all()
    
    # Get group categories and members
    categories = Category.query.filter_by(group_id=group_id).all()
    users = list(group.members)
    
    return render_template("group_expenses.html", 
                         expenses=expenses, 
                         categories=categories, 
                         users=users,
                         group=group,
                         show_participants=True)

@expenses_bp.route("/group/<int:group_id>/add-expense", methods=["GET", "POST"])
@login_required
def add_group_expense(group_id):
    """Add expense to a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    error = None
    
    # Get recent expenses for this group
    recent_expenses = Expense.query.filter_by(group_id=group_id)\
        .order_by(Expense.date.desc()).limit(10).all()
    
    # Get group members and categories
    users = list(group.members)
    categories = Category.query.filter_by(group_id=group_id).all()
    
    if request.method == "POST":
        # Handle redirects to management
        user_id = request.form.get('user_id')
        selected_category_id = request.form.get('category_id')
        
        if user_id == "manage":
            return redirect(url_for("expenses.manage_group_users", 
                                  group_id=group_id,
                                  next=url_for("expenses.add_group_expense", group_id=group_id)))
        if selected_category_id == "manage":
            return redirect(url_for("expenses.manage_group_categories", 
                                  group_id=group_id,
                                  next=url_for("expenses.add_group_expense", group_id=group_id)))

        # Prepare expense data
        expense_data = {
            'amount': request.form.get('amount'),
            'payer_id': user_id,
            'participant_ids': request.form.getlist('participant_ids'),
            'category_id': selected_category_id,
            'category_description': request.form.get('category_description'),
            'date': request.form.get('date') or datetime.today().strftime('%Y-%m-%d'),
            'group_id': group_id  # Add group context
        }

        # Create expense using service
        expense, errors = ExpenseService.create_group_expense(expense_data)
        
        if expense:
            flash(f'Expense of ${expense.amount:.2f} added successfully!', 'success')
            return redirect(url_for("expenses.add_group_expense", group_id=group_id))
        else:
            error = "; ".join(errors)

    return render_template("group_add_expense.html", 
                         error=error, 
                         users=users, 
                         categories=categories, 
                         expenses=recent_expenses,
                         group=group,
                         show_participants=False)

@expenses_bp.route("/store_suggestions")
@login_required
def store_suggestions():
    """Get store suggestions - can be filtered by group if needed"""
    query = request.args.get("q", "").strip()
    group_id = request.args.get("group_id", type=int)
    
    # Use service with optional group filtering
    suggestions = ExpenseService.get_store_suggestions(query, group_id)
    return {"suggestions": suggestions}

@expenses_bp.route("/group/<int:group_id>/delete_expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_group_expense(group_id, expense_id):
    """Delete expense from a group"""
    group = Group.query.get_or_404(group_id)
    expense = Expense.query.get_or_404(expense_id)
    
    # Verify user is member and expense belongs to group
    if current_user not in group.members or expense.group_id != group_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Use service to delete (will recalculate balances)
    success, error = ExpenseService.delete_expense(expense_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error})

@expenses_bp.route("/group/<int:group_id>/edit_expense/<int:expense_id>", methods=["POST"])
@login_required
def edit_group_expense(group_id, expense_id):
    """Edit expense in a group"""
    group = Group.query.get_or_404(group_id)
    expense = Expense.query.get_or_404(expense_id)
    
    # Verify user is member and expense belongs to group
    if current_user not in group.members or expense.group_id != group_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    # Use service to update (will recalculate balances)
    success, error = ExpenseService.update_expense(expense_id, data)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 500

@expenses_bp.route("/group/<int:group_id>/expense_details/<int:expense_id>")
@login_required
def group_expense_details(group_id, expense_id):
    """Get detailed expense information for group expense"""
    group = Group.query.get_or_404(group_id)
    expense = Expense.query.get_or_404(expense_id)
    
    # Verify user is member and expense belongs to group
    if current_user not in group.members or expense.group_id != group_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        participants_data = []
        for participant in expense.participants:
            participants_data.append({
                'user_id': participant.user_id,
                'user_name': participant.user.name,
                'amount_owed': participant.amount_owed
            })
        
        expense_data = {
            'id': expense.id,
            'amount': expense.amount,
            'category': expense.category_obj.name,
            'description': expense.category_description,
            'payer': expense.user.name,
            'payer_id': expense.user_id,
            'date': expense.date.strftime('%Y-%m-%d'),
            'participants': participants_data
        }
        
        return jsonify({'expense': expense_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Group management routes
@expenses_bp.route("/group/<int:group_id>/manage-users", methods=["GET", "POST"])
@login_required
def manage_group_users(group_id):
    """Manage users in a group (admin only)"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is admin
    if not current_user.is_group_admin(group):
        flash('Only group admins can manage users', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_user":
            # For groups, we don't add new users - they join via invite codes
            flash('Users must join using the group invite code', 'info')
    
    # Get current members
    users = list(group.members)
    next_url = request.args.get('next', url_for('groups.detail', group_id=group_id))
    
    return render_template("group_management.html", 
                         group=group,
                         users=users, 
                         next_url=next_url,
                         section='users')

@expenses_bp.route("/group/<int:group_id>/delete_category/<int:cat_id>")
@login_required
def delete_group_category(group_id, cat_id):
    """Delete category from group"""
    group = Group.query.get_or_404(group_id)
    category = Category.query.get_or_404(cat_id)
    
    # Verify category belongs to group and user is member
    if category.group_id != group_id or current_user not in group.members:
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
    
    return redirect(url_for('expenses.manage_group_categories', group_id=group_id))

# Legacy routes for backward compatibility (redirect to dashboard)
@expenses_bp.route("/add-expense", methods=["GET", "POST"])
@login_required
def add_expense():
    """Legacy route - redirect to dashboard"""
    flash('Please select a tracker from your dashboard to add expenses', 'info')
    return redirect(url_for('dashboard.home'))

@expenses_bp.route("/delete_expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    """Legacy route - still works for backward compatibility"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check if user has access (member of group or personal expense)
    if expense.group_id:
        group = Group.query.get(expense.group_id)
        if not group or current_user not in group.members:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    success, error = ExpenseService.delete_expense(expense_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error})

@expenses_bp.route("/edit_expense/<int:expense_id>", methods=["POST"])
@login_required
def edit_expense(expense_id):
    """Legacy route - still works for backward compatibility"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check if user has access
    if expense.group_id:
        group = Group.query.get(expense.group_id)
        if not group or current_user not in group.members:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    success, error = ExpenseService.update_expense(expense_id, data)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 500

@expenses_bp.route("/expense_details/<int:expense_id>")
@login_required
def expense_details(expense_id):
    """Legacy route - still works with access control"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check if user has access
    if expense.group_id:
        group = Group.query.get(expense.group_id)
        if not group or current_user not in group.members:
            return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        participants_data = []
        for participant in expense.participants:
            participants_data.append({
                'user_id': participant.user_id,
                'user_name': participant.user.name,
                'amount_owed': participant.amount_owed
            })
        
        expense_data = {
            'id': expense.id,
            'amount': expense.amount,
            'category': expense.category_obj.name,
            'description': expense.category_description,
            'payer': expense.user.name,
            'payer_id': expense.user_id,
            'date': expense.date.strftime('%Y-%m-%d'),
            'participants': participants_data
        }
        
        return jsonify({'expense': expense_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# In your app/routes/expenses.py - Fix the group_tracker route

@expenses_bp.route('/group/<int:group_id>/tracker')
@login_required
def group_tracker(group_id):
    """Main expense tracker page for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    # Get group categories
    categories = Category.query.filter_by(group_id=group_id).all()
    
    # Get group members
    users = group.members
    
    # Get recent expenses for the group
    expenses = Expense.query.filter_by(group_id=group_id)\
        .order_by(desc(Expense.date)).limit(50).all()
    
    # FIXED: Convert SQLAlchemy objects to dictionaries for JSON serialization
    categories_data = []
    for cat in categories:
        categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'is_default': cat.is_default
        })
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'name': user.name
        })
    
    expenses_data = []
    for exp in expenses:
        expenses_data.append({
            'id': exp.id,
            'amount': float(exp.amount),
            'category_name': exp.category_obj.name if exp.category_obj else 'Unknown',
            'category_description': exp.category_description,
            'user_name': exp.user.name if exp.user else 'Unknown',
            'date': exp.date.strftime('%Y-%m-%d'),
            'payer_id': exp.user_id
        })
    
    return render_template("add_expense_group.html",
        group=group,
        categories=categories,  # Keep original objects for template loops
        users=users,           # Keep original objects for template loops
        expenses=expenses,     # Keep original objects for template loops
        # Add JSON-serializable data for JavaScript
        categories_json=categories_data,
        users_json=users_data,
        expenses_json=expenses_data,
        current_user=current_user
    )

# NEW: Group category management
@expenses_bp.route("/group/<int:group_id>/manage-categories", methods=["GET", "POST"])
@login_required
def manage_group_categories(group_id):
    """Manage categories for a group"""
    group = Group.query.get_or_404(group_id)
    
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_category":
            name = request.form.get("category_name", "").strip()
            if name:
                existing = Category.query.filter_by(name=name, group_id=group_id).first()
                if existing:
                    flash(f"Category '{name}' already exists in this group", 'error')
                else:
                    try:
                        category = Category(name=name, group_id=group_id)
                        db.session.add(category)
                        db.session.commit()
                        flash(f"Category '{name}' added successfully!", 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f"Error adding category: {str(e)}", 'error')
    
    categories = Category.query.filter_by(group_id=group_id).all()
    next_url = request.args.get('next', url_for('expenses.group_tracker', group_id=group_id))
    
    # You can create a simple template for this or reuse/adapt existing management template
    return render_template("manage_categories_group.html", 
                         group=group,
                         categories=categories,
                         next_url=next_url)