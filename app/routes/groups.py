# app/routes/groups.py - Group management routes with financial validation

from flask import Blueprint, jsonify, request, redirect, url_for, render_template_string, flash
from flask_login import login_required, current_user
from models import User, Expense, Category, Group, db, Balance, Settlement, ExpenseParticipant, user_groups
from sqlalchemy import func, desc, or_
from datetime import datetime
from flask import current_app

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')

def check_user_financial_involvement(user_id, group_id):
    """
    Check if user has any financial involvement that prevents leaving the group
    Returns dict with can_leave boolean and details of involvement
    """
    involvement = {
        'balances': [],
        'expenses_paid': [],
        'expenses_participated': [],
        'settlements_made': [],
        'settlements_received': []
    }
    
    details = []
    
    # Check for non-zero balances
    user_balance = Balance.query.filter_by(user_id=user_id, group_id=group_id).first()
    if user_balance and abs(user_balance.amount) > 0.01:
        involvement['balances'].append({
            'amount': round(user_balance.amount, 2)
        })
        if user_balance.amount > 0:
            details.append(f"You are owed ${abs(user_balance.amount):.2f}")
        else:
            details.append(f"You owe ${abs(user_balance.amount):.2f}")
    
    # Check for expenses they paid for
    expenses_paid = Expense.query.filter_by(
        user_id=user_id, 
        group_id=group_id
    ).count()
    
    if expenses_paid > 0:
        involvement['expenses_paid'] = expenses_paid
        details.append(f"You have paid for {expenses_paid} expense(s)")
    
    # Check for expenses they participated in
    expenses_participated = db.session.query(ExpenseParticipant).join(Expense).filter(
        ExpenseParticipant.user_id == user_id,
        Expense.group_id == group_id,
        ExpenseParticipant.user_id != Expense.user_id  # Exclude expenses they paid for (already counted above)
    ).count()
    
    if expenses_participated > 0:
        involvement['expenses_participated'] = expenses_participated
        details.append(f"You have participated in {expenses_participated} expense(s)")
    
    # Check for settlements they made
    settlements_made = Settlement.query.filter_by(
        payer_id=user_id,
        group_id=group_id
    ).count()
    
    if settlements_made > 0:
        involvement['settlements_made'] = settlements_made
        details.append(f"You have made {settlements_made} settlement(s)")
    
    # Check for settlements they received
    settlements_received = Settlement.query.filter_by(
        receiver_id=user_id,
        group_id=group_id
    ).count()
    
    if settlements_received > 0:
        involvement['settlements_received'] = settlements_received
        details.append(f"You have received {settlements_received} settlement(s)")
    
    # User can leave only if they have no financial involvement
    can_leave = (
        len(involvement['balances']) == 0 and
        involvement['expenses_paid'] == 0 and
        involvement['expenses_participated'] == 0 and
        involvement['settlements_made'] == 0 and
        involvement['settlements_received'] == 0
    )
    
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

        data = request.get_json() if request.is_json else {}
        is_creator = group.creator_id == current_user.id
        is_admin = current_user.is_group_admin(group)
        
        # Handle creator leaving (must transfer admin rights)
        if is_creator:
            new_admin_id = data.get('new_admin_id')
            if not new_admin_id:
                return jsonify({
                    'success': False, 
                    'error': 'As group creator, you must select a new admin before leaving'
                }), 400
            
            # Validate new admin
            new_admin = User.query.get(new_admin_id)
            if not new_admin:
                return jsonify({'success': False, 'error': 'Selected user not found'}), 400
            
            if new_admin not in group.members:
                return jsonify({'success': False, 'error': 'Selected user is not a group member'}), 400
            
            if new_admin.id == current_user.id:
                return jsonify({'success': False, 'error': 'You cannot transfer admin rights to yourself'}), 400
            
            # Check if group has at least 2 members
            if group.get_member_count() < 2:
                return jsonify({
                    'success': False, 
                    'error': 'Cannot leave group with only one member. Delete the group instead.'
                }), 400
            
            # Transfer admin rights
            group.creator_id = new_admin.id
            
            # Update the association table to make new admin have admin role
            # First remove old admin role entry for new admin (if any)
            stmt_remove = user_groups.update().where(
                user_groups.c.user_id == new_admin.id,
                user_groups.c.group_id == group.id
            ).values(role='admin')
            db.session.execute(stmt_remove)
            
            current_app.logger.info(f"Transferred admin rights from {current_user.name} to {new_admin.name} for group {group.name}")
        
        # Remove user from group
        group.remove_member(current_user)
        
        db.session.commit()
        
        group_name = group.name
        success_message = f'You have successfully left "{group_name}"'
        
        if is_creator:
            success_message += f' and transferred admin rights to {new_admin.name}'
        
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