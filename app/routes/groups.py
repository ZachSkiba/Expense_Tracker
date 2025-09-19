# app/routes/groups.py - Group management routes (FIXED)

from flask import Blueprint, request, redirect, url_for, render_template_string, flash
from flask_login import login_required, current_user
from models import User, Expense, Category, Group, db
from sqlalchemy import func, desc
from datetime import datetime

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')

@groups_bp.route('/')
@login_required
def index():
    """Groups management page"""
    user_groups = current_user.groups
    from app.templates.group_templates import get_groups_template
    return render_template_string(get_groups_template(), user_groups=user_groups)

@groups_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new expense group"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Group name is required', 'error')
            from app.templates.group_templates import get_create_group_template
            return render_template_string(get_create_group_template())
        
        if len(name) < 3:
            flash('Group name must be at least 3 characters', 'error')
            from app.templates.group_templates import get_create_group_template
            return render_template_string(get_create_group_template())
        
        try:
            # Create the group
            group = Group(
                name=name,
                description=description if description else f"Shared expense group: {name}",
                creator_id=current_user.id,
                invite_code=Group.generate_invite_code()
            )
            
            db.session.add(group)
            db.session.flush()  # Get group ID
            
            # Add creator as admin member
            group.add_member(current_user, role='admin')
            
            # Create default categories for the group
            default_categories = [
                'Groceries',
                'Transportation', 
                'Rent',
                'Utilities',
                'Entertainment',
                'Healthcare',
                'Dining Out',
                'Shopping',
                'Education',
                'Travel',
                'Other'
            ]
            
            for cat_name in default_categories:
                category = Category(
                    name=cat_name,
                    group_id=group.id,
                    is_default=True
                )
                db.session.add(category)
            
            db.session.commit()
            
            flash(f'Group "{name}" created successfully!', 'success')
            # FIXED: Go to the expense tracker, not group detail
            return redirect(url_for('expenses.group_tracker', group_id=group.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the group', 'error')
            print(f"Group creation error: {e}")
    
    from app.templates.group_templates import get_create_group_template
    return render_template_string(get_create_group_template())

@groups_bp.route('/join', methods=['GET', 'POST'])
@login_required
def join():
    """Join a group using invite code"""
    if request.method == 'POST':
        invite_code = request.form.get('invite_code', '').strip().upper()
        
        if not invite_code:
            flash('Invite code is required', 'error')
            from app.templates.group_templates import get_join_group_template
            return render_template_string(get_join_group_template())
        
        group = Group.query.filter_by(invite_code=invite_code, is_active=True).first()
        
        if not group:
            flash('Invalid invite code', 'error')
            from app.templates.group_templates import get_join_group_template
            return render_template_string(get_join_group_template())
        
        if current_user in group.members:
            flash('You are already a member of this group', 'info')
            return redirect(url_for('groups.detail', group_id=group.id))
        
        try:
            group.add_member(current_user, role='member')
            db.session.commit()
            
            flash(f'Successfully joined "{group.name}"!', 'success')
            return redirect(url_for('groups.detail', group_id=group.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while joining the group', 'error')
            print(f"Join group error: {e}")
    
    from app.templates.group_templates import get_join_group_template
    return render_template_string(get_join_group_template())

@groups_bp.route('/<int:group_id>')
@login_required
def detail(group_id):
    """Group detail page"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('groups.index'))
    
    # Get recent expenses
    recent_expenses = Expense.query.filter_by(group_id=group_id)\
        .order_by(desc(Expense.date)).limit(10).all()
    
    # Get group categories
    group_categories = Category.query.filter_by(group_id=group_id).all()
    
    # Calculate total spent this month
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_total = db.session.query(func.sum(Expense.amount)).filter(
        Expense.group_id == group_id,
        Expense.date >= start_of_month.date()
    ).scalar() or 0
    
    # Get user's balance in this group
    user_balance = current_user.get_group_balance(group_id)
    
    is_admin = current_user.is_group_admin(group)
    
    from app.templates.group_templates import get_group_detail_template
    return render_template_string(
        get_group_detail_template(),
        group=group,
        recent_expenses=recent_expenses,
        group_categories=group_categories,
        monthly_total=monthly_total,
        user_balance=user_balance,
        is_admin=is_admin,
        abs=abs
    )

@groups_bp.route('/<int:group_id>/leave', methods=['POST'])
@login_required
def leave(group_id):
    """Leave a group"""
    group = Group.query.get_or_404(group_id)
    
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('groups.index'))
    
    if group.creator_id == current_user.id:
        flash('You cannot leave a group you created. Transfer ownership first.', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))

    try:
        group.remove_member(current_user)
        db.session.commit()
        
        flash(f'You have left "{group.name}"', 'success')
        return redirect(url_for('groups.index'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while leaving the group', 'error')
        return redirect(url_for('groups.detail', group_id=group_id))