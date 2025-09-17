# app/routes/dashboard.py - Updated with Personal Tracker Creation

from flask import Blueprint, request, redirect, url_for, render_template, flash
from flask_login import login_required, current_user
from models import User, Expense, Category, Group, db
from sqlalchemy import func, desc
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def home():
    """Dashboard showing personal trackers and groups"""
    
    # Get user's groups (includes both personal trackers and shared groups)
    user_groups = current_user.groups
    
    # Separate personal trackers from shared groups
    personal_trackers = []
    shared_groups = []
    
    for group in user_groups:
        if group.get_member_count() == 1 and group.creator_id == current_user.id:
            personal_trackers.append(group)
        else:
            shared_groups.append(group)
    
    # Get recent personal expenses across all personal trackers
    personal_tracker_ids = [tracker.id for tracker in personal_trackers]
    personal_expenses = []
    personal_monthly_total = 0
    
    if personal_tracker_ids:
        personal_expenses = Expense.query.filter(
            Expense.group_id.in_(personal_tracker_ids)
        ).order_by(desc(Expense.date)).limit(5).all()
        
        # Calculate personal spending this month
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        personal_monthly_total = db.session.query(func.sum(Expense.amount)).filter(
            Expense.group_id.in_(personal_tracker_ids),
            Expense.date >= start_of_month.date()
        ).scalar() or 0
    
    # Get group balances for shared groups
    group_balances = {}
    for group in shared_groups:
        balance = current_user.get_group_balance(group.id)
        group_balances[group.id] = balance
    
    # Get recent group activities from shared groups
    group_activities = []
    if shared_groups:
        shared_group_ids = [g.id for g in shared_groups]
        recent_group_expenses = Expense.query.filter(
            Expense.group_id.in_(shared_group_ids)
        ).order_by(desc(Expense.date)).limit(5).all()
        
        for expense in recent_group_expenses:
            group_activities.append({
                'type': 'expense',
                'expense': expense,
                'group': expense.group,
                'user': expense.user
            })
    
    return render_template(
        'groups/dashboard_templates.html',
        user=current_user,
        personal_expenses=personal_expenses,
        personal_trackers=personal_trackers,
        user_groups=shared_groups,  # Only shared groups for the groups section
        group_activities=group_activities,
        personal_monthly_total=personal_monthly_total,
        group_balances=group_balances
    )

@dashboard_bp.route('/create-personal-tracker', methods=['POST'])
@login_required
def create_personal_tracker():
    """Create a new personal expense tracker (group with one member)"""
    
    # Get tracker name from form, or use default
    tracker_name = request.form.get('name', '').strip()
    if not tracker_name:
        tracker_name = f"{current_user.name}'s Personal Expenses"
    
    # Check if name already exists for this user
    existing_tracker = Group.query.filter_by(
        name=tracker_name,
        creator_id=current_user.id
    ).first()
    
    if existing_tracker:
        # Add a number to make it unique
        counter = 1
        base_name = tracker_name
        while existing_tracker:
            tracker_name = f"{base_name} ({counter})"
            existing_tracker = Group.query.filter_by(
                name=tracker_name,
                creator_id=current_user.id
            ).first()
            counter += 1
    
    try:
        # Create the personal tracker (group)
        tracker = Group(
            name=tracker_name,
            description=f"Personal expense tracker for {current_user.name}",
            creator_id=current_user.id,
            invite_code=Group.generate_invite_code()
        )
        
        db.session.add(tracker)
        db.session.flush()  # Get tracker ID
        
        # Add creator as the only member
        tracker.add_member(current_user, role='admin')
        
        # Create default categories for the personal tracker
        default_categories = [
            'Groceries',
            'Transportation', 
            'Rent & Housing',
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
                group_id=tracker.id,
                is_default=True
            )
            db.session.add(category)
        
        db.session.commit()
        
        flash(f'Personal tracker "{tracker_name}" created successfully!', 'success')
        return redirect(url_for('groups.detail', group_id=tracker.id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating personal tracker: {e}")
        flash('An error occurred while creating your personal tracker', 'error')
        return redirect(url_for('dashboard.home'))