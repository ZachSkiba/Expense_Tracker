# app/routes/dashboard.py - FIXED with correct template variables

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
    
    # Get user's groups
    user_groups = current_user.groups
    
    # Separate based on description pattern (since personal trackers have specific description)
    personal_trackers = []
    shared_groups = []
    
    for group in user_groups:
        # Personal trackers created via dashboard have this specific description pattern
        if (group.description and 
            "Personal expense tracker for" in group.description):
            personal_trackers.append(group)
        else:
            shared_groups.append(group)
    
    # Get group balances for shared groups
    group_balances = {}
    for group in shared_groups:
        balance = current_user.get_group_balance(group.id)
        group_balances[group.id] = balance
    
    return render_template(
        'dashboard/dashboard_templates.html',
        user=current_user,
        personal_trackers=personal_trackers,
        user_groups=shared_groups,
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
    
    # ENSURE the name indicates it's personal
    if not ("Personal" in tracker_name or "personal" in tracker_name.lower()):
        if not tracker_name.endswith("'s Expenses"):
            tracker_name = f"{tracker_name} - Personal"
    
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
                group_id=tracker.id,
                is_default=True
            )
            db.session.add(category)
        
        db.session.commit()
        
        flash(f'Personal tracker "{tracker_name}" created successfully!', 'success')
        return redirect(url_for('expenses.group_tracker', group_id=tracker.id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating personal tracker: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while creating your personal tracker', 'error')
        return redirect(url_for('dashboard.home'))