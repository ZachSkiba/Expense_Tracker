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
    
    # Get group balances for shared groups
    group_balances = {}
    for group in shared_groups:
        balance = current_user.get_group_balance(group.id)
        group_balances[group.id] = balance
    
    # FIXED: Pass all required template variables
    return render_template(
        'groups/dashboard_templates.html',
        user=current_user,
        personal_trackers=personal_trackers,
        user_groups=shared_groups,  # Only shared groups for the groups section
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
        return redirect(url_for('expenses.group_tracker', group_id=tracker.id))  # FIXED: Go to tracker directly
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating personal tracker: {e}")
        import traceback
        traceback.print_exc()  # Print full error for debugging
        flash('An error occurred while creating your personal tracker', 'error')
        return redirect(url_for('dashboard.home'))
    
    # Add this temporary debug route to your dashboard.py to test

@dashboard_bp.route('/debug-create-test', methods=['GET', 'POST'])
@login_required
def debug_create_test():
    """Debug route to test group creation"""
    if request.method == 'POST':
        print("=== DEBUG: POST request received ===")
        print(f"Form data: {request.form}")
        
        # Try to create a simple group
        try:
            test_group = Group(
                name="Test Group",
                description="Debug test group",
                creator_id=current_user.id,
                invite_code=Group.generate_invite_code()
            )
            
            db.session.add(test_group)
            db.session.flush()
            
            print(f"Group created with ID: {test_group.id}")
            
            # Add member
            test_group.add_member(current_user, role='admin')
            
            # Create one test category
            category = Category(
                name='Test Category',
                group_id=test_group.id,
                is_default=True
            )
            db.session.add(category)
            
            db.session.commit()
            print("=== DEBUG: Group created successfully ===")
            
            flash('Debug group created successfully!', 'success')
            return redirect(url_for('dashboard.home'))
            
        except Exception as e:
            db.session.rollback()
            print(f"=== DEBUG: Error creating group: {e} ===")
            import traceback
            traceback.print_exc()
            flash(f'Debug error: {str(e)}', 'error')
            return redirect(url_for('dashboard.home'))
    
    # GET request - show simple form
    return '''
    <form method="post">
        <button type="submit">Create Debug Group</button>
    </form>
    '''