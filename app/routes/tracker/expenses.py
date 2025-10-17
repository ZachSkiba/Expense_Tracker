# app/routes/expenses.py - MINIMAL CHANGES: Just fix data filtering and template

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime

from sqlalchemy import desc
from models import db, Expense, User, Category, ExpenseParticipant, Balance, Group, user_groups
from app.services.tracker.expense_service import ExpenseService
from app.services.tracker.user_service import UserService
from app.services.tracker.category_service import CategoryService


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

# MAIN ROUTE: All trackers use this single route
@expenses_bp.route('/group/<int:group_id>/tracker', methods=['GET', 'POST'])
@login_required
def group_tracker(group_id):
    """
    UNIFIED expense tracker for both personal and group trackers.
    Personal trackers are just groups with one member.
    """
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    error = None
    
    # Handle POST request (adding new expense)
    if request.method == 'POST':
        # Handle redirects to management
        user_id = request.form.get('user_id')
        selected_category_id = request.form.get('category_id')
        
        if user_id == "manage":
            return redirect(url_for("expenses.manage_group_users", 
                                  group_id=group_id,
                                  next=url_for("expenses.group_tracker", group_id=group_id)))
        if selected_category_id == "manage":
            return redirect(url_for("expenses.manage_group_categories", 
                                  group_id=group_id,
                                  next=url_for("expenses.group_tracker", group_id=group_id)))

        # Prepare expense data
        expense_data = {
            'amount': request.form.get('amount'),
            'payer_id': user_id,
            'participant_ids': request.form.getlist('participant_ids'),
            'category_id': selected_category_id,
            'category_description': request.form.get('category_description'),
            'date': request.form.get('date') or datetime.today().strftime('%Y-%m-%d'),
            'group_id': group_id
        }

        # Create expense using service
        expense, errors = ExpenseService.create_group_expense(expense_data)
        
        if expense:
            flash(f'Expense of ${expense.amount:.2f} added successfully!', 'success')
            return redirect(url_for("expenses.group_tracker", group_id=group_id))
        else:
            error = "; ".join(errors)
    
    # GET request - show the tracker page
    
   # Get group categories - ordered by display_order
    categories = Category.query.filter_by(group_id=group_id).order_by(
        Category.display_order.nullslast(), 
        Category.id
    ).all()

    # Get group members - ordered by display_order from user_groups
    users = db.session.query(User).join(user_groups).filter(
        user_groups.c.group_id == group_id
    ).order_by(
        user_groups.c.display_order.nullslast(),
        User.id
    ).all()
    
    # Get recent expenses for the group
    expenses = Expense.query.filter_by(group_id=group_id)\
        .order_by(desc(Expense.date)).limit(50).all()
    
    # Set show_participants based on group size
    show_participants = (group.get_member_count() > 1)
    
    # Convert SQLAlchemy objects to dictionaries for JSON serialization
    categories_data = []
    for cat in categories:
        categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'is_default': getattr(cat, 'is_default', False)
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
    
    # Use the ORIGINAL add_expense.html template with correct data
    return render_template("tracker/add_expense.html",
        error=error,
        group=group,
        categories=categories,       # Original objects for template loops
        users=users,                # Original objects for template loops  
        expenses=expenses,           # Original objects for template loops
        categories_json=categories_data,  # JSON-safe data for JavaScript
        users_json=users_data,           # JSON-safe data for JavaScript
        expenses_json=expenses_data,     # JSON-safe data for JavaScript
        show_participants=show_participants,  # Add this flag
        is_personal_tracker=group.is_personal_tracker,  
        group_creator_id=group.creator_id,             
        # Add form data for persistence on errors
        amount=request.form.get('amount', '') if request.method == 'POST' else '',
        selected_category_id=request.form.get('category_id', '') if request.method == 'POST' else '',
        category_description=request.form.get('category_description', '') if request.method == 'POST' else '',
        selected_user_id=request.form.get('user_id', '') if request.method == 'POST' else '',
        date=request.form.get('date', '') if request.method == 'POST' else ''
    )

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
    
    # Get group categories and members for the template
    # Get group categories and members for the template - ordered
    categories = [{"id": c.id, "name": c.name} for c in Category.query.filter_by(group_id=group_id).order_by(
        Category.display_order.nullslast(), 
        Category.id
    ).all()]
    users = [{"id": u.id, "name": u.name} for u in db.session.query(User).join(user_groups).filter(
        user_groups.c.group_id == group_id
    ).order_by(
        user_groups.c.display_order.nullslast(),
        User.id
    ).all()]
    
    # Set show_participants based on group size
    show_participants = (group.get_member_count() > 1)
    
    return render_template("tracker/expenses.html", 
                         expenses=expenses, 
                         categories=categories, 
                         users=users,
                         group=group,
                         show_participants=show_participants)

@expenses_bp.route("/store_suggestions")
@login_required
def store_suggestions():
    """Get store suggestions - group-filtered"""
    query = request.args.get("q", "").strip()
    group_id = request.args.get("group_id", type=int)
    
    # Use service with group filtering
    suggestions = ExpenseService.get_store_suggestions(query, group_id)
    return {"suggestions": suggestions}

# API ROUTES - All work with group context
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

# Legacy routes for backward compatibility - now work with group context
@expenses_bp.route("/delete_expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    """Legacy route - still works with group access control"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Check if user has access (member of group)
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
    """Legacy route - still works with group access control"""
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
