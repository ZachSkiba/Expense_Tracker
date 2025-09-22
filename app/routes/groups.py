# app/routes/groups.py - Group management routes (FIXED)

from flask import Blueprint, jsonify, request, redirect, url_for, render_template_string, flash
from flask_login import login_required, current_user
from models import User, Expense, Category, Group, db
from sqlalchemy import func, desc
from datetime import datetime
from flask import current_app

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
            return redirect(url_for('dashboard.home', group_id=group.id))
        
        try:
            group.add_member(current_user, role='member')
            db.session.commit()
            
            flash(f'Successfully joined "{group.name}"!', 'success')
            return redirect(url_for('dashboard.home', group_id=group.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while joining the group', 'error')
            print(f"Join group error: {e}")
    
    from app.templates.group_templates import get_join_group_template
    return render_template_string(get_join_group_template())

@groups_bp.route('/<int:group_id>/leave', methods=['POST'])
@login_required
def leave(group_id):
    """Leave a group"""
    group = Group.query.get_or_404(group_id)
    
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    if group.creator_id == current_user.id:
        flash('You cannot leave a group you created. Transfer ownership first.', 'error')
        return redirect(url_for('dashboard.home', group_id=group_id))

    try:
        group.remove_member(current_user)
        db.session.commit()
        
        flash(f'You have left "{group.name}"', 'success')
        return redirect(url_for('dashboard.home'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while leaving the group', 'error')
        return redirect(url_for('dashboard.home', group_id=group_id))
    

@groups_bp.route('/<int:group_id>/update', methods=['POST'])
@login_required
def update_group(group_id):
    """Update group name and description from settings"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user has permission to edit (admin or creator)
    if current_user not in group.members:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    if not current_user.is_group_admin(group) and group.creator_id != current_user.id:
        return jsonify({"success": False, "error": "Only group admins can edit group information"}), 403
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Validate and update name
        new_name = data.get('name', '').strip()
        if not new_name:
            return jsonify({"success": False, "error": "Group name cannot be empty"}), 400
        
        if len(new_name) > 100:
            return jsonify({"success": False, "error": "Group name must be less than 100 characters"}), 400
        
        # Validate and update description
        new_description = data.get('description', '').strip()
        if len(new_description) > 500:
            return jsonify({"success": False, "error": "Description must be less than 500 characters"}), 400
        
        # Update the group
        group.name = new_name
        group.description = new_description if new_description else None
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Group updated successfully",
            "name": group.name,
            "description": group.description
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating group {group_id}: {e}")
        return jsonify({"success": False, "error": "An error occurred while updating the group"}), 500