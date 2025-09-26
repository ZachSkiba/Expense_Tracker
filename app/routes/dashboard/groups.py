# app/routes/groups.py - Group management routes with financial validation

from flask import Blueprint, jsonify, request, redirect, url_for, render_template, flash
from flask_login import login_required, current_user
from models import User, Expense, Category, Group, db, Balance, Settlement, ExpenseParticipant, user_groups
from sqlalchemy import func, desc, or_
from datetime import datetime
from flask import current_app

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')

def check_user_financial_involvement(user_id, group_id):
    """
    Check if user has any financial involvement that prevents leaving the group
    Only checks for non-zero balances - historical activity is irrelevant if balance is settled
    Returns dict with can_leave boolean and details of involvement
    """
    involvement = {
        'balances': [],
        'expenses_paid': 0,
        'expenses_participated': 0,
        'settlements_made': 0,
        'settlements_received': 0
    }
    
    details = []
    
    # Check for non-zero balances - this is the ONLY thing that matters for leaving
    user_balance = Balance.query.filter_by(user_id=user_id, group_id=group_id).first()
    if user_balance and abs(user_balance.amount) > 0.01:
        involvement['balances'].append({
            'amount': round(user_balance.amount, 2)
        })
        if user_balance.amount > 0:
            details.append(f"You are owed ${abs(user_balance.amount):.2f}")
        else:
            details.append(f"You owe ${abs(user_balance.amount):.2f}")
    
    # Still collect historical data for display purposes, but don't use it to prevent leaving
    expenses_paid = Expense.query.filter_by(user_id=user_id, group_id=group_id).count()
    expenses_participated = db.session.query(ExpenseParticipant).join(Expense).filter(
        ExpenseParticipant.user_id == user_id,
        Expense.group_id == group_id,
        ExpenseParticipant.user_id != Expense.user_id
    ).count()
    settlements_made = Settlement.query.filter_by(payer_id=user_id, group_id=group_id).count()
    settlements_received = Settlement.query.filter_by(receiver_id=user_id, group_id=group_id).count()
    
    involvement['expenses_paid'] = expenses_paid
    involvement['expenses_participated'] = expenses_participated
    involvement['settlements_made'] = settlements_made
    involvement['settlements_received'] = settlements_received
    
    # User can leave ONLY if they have no outstanding balance
    # Historical activity doesn't matter if all debts are settled
    can_leave = len(involvement['balances']) == 0
    
    return {
        'can_leave': can_leave,
        'involvement': involvement,
        'details': details
    }

@groups_bp.route('/')
@login_required
def index():
    """Groups management page"""
    user_groups = current_user.groups
    return render_template('dashboard/groups.html', user_groups=user_groups)

@groups_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new expense group"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Group name is required', 'error')
            return render_template('dashboard/create_group.html')
        
        if len(name) < 3:
            flash('Group name must be at least 3 characters', 'error')
            return render_template('dashboard/create_group.html')
        
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
    
    return render_template('dashboard/create_group.html')

@groups_bp.route('/join', methods=['GET', 'POST'])
@login_required
def join():
    """Join a group using invite code"""
    if request.method == 'POST':
        invite_code = request.form.get('invite_code', '').strip().upper()
        
        if not invite_code:
            flash('Invite code is required', 'error')
            return render_template('dashboard/join_group.html')
        
        group = Group.query.filter_by(invite_code=invite_code, is_active=True).first()
        
        if not group:
            flash('Invalid invite code', 'error')
            return render_template('dashboard/join_group.html')
        
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
    
    return render_template('dashboard/join_group.html')

@groups_bp.route('/<int:group_id>/check-leave-eligibility', methods=['GET'])
@login_required
def check_leave_eligibility(group_id):
    """Check if current user can leave the group"""
    group = Group.query.get_or_404(group_id)
    
    if current_user not in group.members:
        return jsonify({'error': 'You are not a member of this group'}), 403
    
    financial_check = check_user_financial_involvement(current_user.id, group_id)
    
    return jsonify({
        'can_leave': financial_check['can_leave'],
        'details': financial_check['details'],
        'involvement': financial_check['involvement']
    })

@groups_bp.route('/<int:group_id>/manage-admins', methods=['POST'])
@login_required
def manage_admins(group_id):
    """Manage admin rights for group members (admin only)"""
    group = Group.query.get_or_404(group_id)
    
    # Only current admin/creator can manage admin rights
    if not (group.creator_id == current_user.id or current_user.is_group_admin(group)):
        return jsonify({'error': 'Only group admins can manage admin rights'}), 403

    try:
        data = request.get_json()
        admin_ids = data.get('admin_ids', [])
        
        if not admin_ids:
            return jsonify({'error': 'At least one admin must be selected'}), 400
        
        # Validate all selected admins are group members
        selected_users = User.query.filter(User.id.in_(admin_ids)).all()
        for user in selected_users:
            if user not in group.members:
                return jsonify({'error': f'{user.name} is not a group member'}), 400
        
        # Update admin rights for all group members
        for member in group.members:
            if member.id in admin_ids:
                # Make this member an admin
                stmt = user_groups.update().where(
                    user_groups.c.user_id == member.id,
                    user_groups.c.group_id == group.id
                ).values(role='admin')
                db.session.execute(stmt)
            else:
                # Make this member a regular member (unless they're the original creator)
                if member.id != group.creator_id:
                    stmt = user_groups.update().where(
                        user_groups.c.user_id == member.id,
                        user_groups.c.group_id == group.id
                    ).values(role='member')
                    db.session.execute(stmt)
        
        # Update the group creator if needed (first admin in the list becomes creator)
        new_creator_id = admin_ids[0]
        if new_creator_id != group.creator_id:
            group.creator_id = new_creator_id
        
        db.session.commit()
        
        admin_names = [user.name for user in selected_users]
        current_app.logger.info(f"Updated admin rights for group {group.name}: {', '.join(admin_names)}")
        
        return jsonify({
            'success': True,
            'message': f'Admin rights updated successfully',
            'admins': admin_names
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error managing admin rights for group {group_id}: {e}")
        return jsonify({'error': 'An error occurred while updating admin rights'}), 500

@groups_bp.route('/<int:group_id>/leave', methods=['POST'])
@login_required
def leave(group_id):
    """Leave a group with financial involvement validation"""
    group = Group.query.get_or_404(group_id)
    
    if current_user not in group.members:
        return jsonify({'success': False, 'error': 'You are not a member of this group'}), 403

    try:
        # Check for financial involvement before allowing leave
        financial_check = check_user_financial_involvement(current_user.id, group_id)
        if not financial_check['can_leave']:
            return jsonify({
                'success': False, 
                'error': 'Cannot leave group with outstanding financial obligations',
                'details': financial_check['details'],
                'involvement': financial_check['involvement']
            }), 400

        is_creator = group.creator_id == current_user.id
        is_admin = current_user.is_group_admin(group)
        
        # Creators/admins cannot leave without transferring admin rights first
        if is_creator or is_admin:
            return jsonify({
                'success': False, 
                'error': 'As a group admin, you must transfer admin rights before leaving the group. Use the "Transfer Admin Rights" feature above.'
            }), 400
        
        # Check if group has at least 2 members (so it won't be empty)
        if group.get_member_count() <= 1:
            return jsonify({
                'success': False, 
                'error': 'Cannot leave group with only one member. Ask an admin to delete the group instead.'
            }), 400
        
        # Remove user from group
        group.remove_member(current_user)
        
        db.session.commit()
        
        group_name = group.name
        success_message = f'You have successfully left "{group_name}"'
        
        return jsonify({
            'success': True,
            'message': success_message,
            'redirect_url': url_for('dashboard.home')
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error leaving group {group_id}: {e}")
        return jsonify({
            'success': False, 
            'error': 'An error occurred while leaving the group'
        }), 500

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
    
    
@groups_bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    """Delete a group (admin only)"""
    try:
        # Get the group
        group = Group.query.get_or_404(group_id)
        
        # Check if current user is admin (creator or has admin role)
        if not (group.creator_id == current_user.id or current_user.is_group_admin(group)):
            return jsonify({
                'success': False,
                'error': 'Only group admins can delete the group'
            }), 403
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        confirmation_text = data.get('confirmation', '').strip().lower()
        
        # Validate confirmation text
        if confirmation_text != 'delete':
            return jsonify({
                'success': False,
                'error': 'Please type "delete" to confirm deletion'
            }), 400
        
        # Store group name for success message
        group_name = group.name
        
        # Delete the group (this should cascade delete related records)
        # Note: Make sure your database relationships are set up with proper cascading
        db.session.delete(group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Group "{group_name}" has been permanently deleted',
            'redirect_url': url_for('dashboard.home')
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting group {group_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while deleting the group'
        }), 500