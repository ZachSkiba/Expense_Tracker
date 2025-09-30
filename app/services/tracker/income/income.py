# app/routes/tracker/income.py - Income tracking routes

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import db, User, Group, user_groups
from models.income_models import IncomeCategory, IncomeEntry
from datetime import datetime, date
import logging

# Set up logging
logger = logging.getLogger(__name__)

income_bp = Blueprint('income', __name__, url_prefix='/api/income')

@income_bp.route('/entries/<int:group_id>', methods=['GET'])
@login_required
def get_income_entries_api(group_id):
    """Get all income entries for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get income entries for this group only
        income_entries = IncomeEntry.query.filter_by(group_id=group_id).order_by(IncomeEntry.date.desc()).all()
        
        entries_data = []
        for entry in income_entries:
            entries_data.append({
                'id': entry.id,
                'amount': entry.amount,
                'income_category_id': entry.income_category_id,
                'income_category_name': entry.income_category_obj.name,
                'description': entry.description,
                'user_id': entry.user_id,
                'user_name': entry.user.name,
                'group_id': entry.group_id,
                'date': entry.date.isoformat(),
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'income_entries': entries_data
        })
    
    except Exception as e:
        logger.error(f"Error getting income entries for group {group_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading income entries'
        }), 500

@income_bp.route('/entries/<int:group_id>', methods=['POST'])
@login_required
def create_income_entry_api(group_id):
    """Create a new income entry for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.json
        logger.info(f"[CREATE_INCOME] Received data for income entry in group {group_id}: {data}")
        
        # Validate required fields
        required_fields = ['amount', 'income_category_id', 'user_id', 'date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Convert string IDs to integers for database queries
        try:
            user_id = int(data['user_id'])
            income_category_id = int(data['income_category_id'])
            amount = float(data['amount'])
        except (ValueError, TypeError) as e:
            logger.error(f"[CREATE_INCOME] Error converting values: {e}")
            return jsonify({
                'success': False,
                'message': 'Invalid data format'
            }), 400
        
        # Validate that user is a group member
        user = User.query.get(user_id)
        if not user or user not in group.members:
            return jsonify({
                'success': False,
                'message': 'User must be a group member'
            }), 400
        
        # Validate that income category exists and belongs to this group
        income_category = IncomeCategory.query.filter_by(id=income_category_id, group_id=group_id).first()
        if not income_category:
            return jsonify({
                'success': False,
                'message': 'Invalid income category selected'
            }), 400
        
        # Parse date
        try:
            entry_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        # Create income entry
        income_entry = IncomeEntry(
            amount=amount,
            income_category_id=income_category_id,
            description=data.get('description', '').strip() or None,
            user_id=user_id,
            group_id=group_id,
            date=entry_date
        )
        
        db.session.add(income_entry)
        db.session.flush()  # Get the income_entry.id before committing

        logger.info(f"[CREATE_INCOME] Created income entry with ID: {income_entry.id}")

        # Handle allocations if provided
        allocations_data = data.get('allocations', [])
        if allocations_data:
            from models.income_models import IncomeAllocation, IncomeAllocationCategory
            
            logger.info(f"[CREATE_INCOME] Processing {len(allocations_data)} allocations")
            
            for allocation_data in allocations_data:
                # Validate category belongs to group
                category = IncomeAllocationCategory.query.filter_by(
                    id=allocation_data['allocation_category_id'],
                    group_id=group_id
                ).first()
                
                if not category:
                    db.session.rollback()
                    return jsonify({
                        'success': False,
                        'message': 'Invalid allocation category'
                    }), 400
                
                # Create allocation
                allocation = IncomeAllocation(
                    amount=float(allocation_data['amount']),
                    allocation_category_id=int(allocation_data['allocation_category_id']),
                    notes=allocation_data.get('notes') or None,
                    income_entry_id=income_entry.id
                )
                db.session.add(allocation)
            
            logger.info(f"[CREATE_INCOME] Added {len(allocations_data)} allocations")

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Income entry created successfully',
            'income_entry_id': income_entry.id
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"[CREATE_INCOME] Error creating income entry: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error creating income entry'
        }), 500

@income_bp.route('/entries/<int:group_id>/<int:entry_id>', methods=['PUT'])
@login_required
def update_income_entry_api(group_id, entry_id):
    """Update an existing income entry"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        logger.info(f"[UPDATE_INCOME] PUT request received for entry {entry_id} in group {group_id}")
        
        # Get and validate JSON data
        if not request.is_json:
            logger.error(f"[UPDATE_INCOME] ERROR: Request is not JSON")
            return jsonify({
                'success': False,
                'message': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        if not data:
            logger.error(f"[UPDATE_INCOME] ERROR: No JSON data received")
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
            
        logger.info(f"[UPDATE_INCOME] Received data: {data}")
        
        # Check if income entry exists and belongs to the group
        existing_entry = IncomeEntry.query.filter_by(id=entry_id, group_id=group_id).first()
        if not existing_entry:
            logger.error(f"[UPDATE_INCOME] ERROR: Entry {entry_id} not found in group {group_id}")
            return jsonify({
                'success': False,
                'message': f'Income entry {entry_id} not found in this group'
            }), 404
        
        logger.info(f"[UPDATE_INCOME] Found existing entry: {existing_entry.id}")
        
        # Update fields if provided
        if 'amount' in data:
            try:
                existing_entry.amount = float(data['amount'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Invalid amount format'
                }), 400
        
        if 'income_category_id' in data:
            try:
                category_id = int(data['income_category_id'])
                # Validate category belongs to group
                category = IncomeCategory.query.filter_by(id=category_id, group_id=group_id).first()
                if not category:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid income category selected'
                    }), 400
                existing_entry.income_category_id = category_id
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Invalid category format'
                }), 400
        
        if 'description' in data:
            existing_entry.description = data['description'].strip() or None
        
        if 'user_id' in data:
            try:
                user_id = int(data['user_id'])
                user = User.query.get(user_id)
                if not user or user not in group.members:
                    return jsonify({
                        'success': False,
                        'message': 'User must be a group member'
                    }), 400
                existing_entry.user_id = user_id
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Invalid user format'
                }), 400
        
        if 'date' in data:
            try:
                existing_entry.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        # Update timestamp
        existing_entry.updated_at = datetime.utcnow()
        
        # Commit the changes
        db.session.commit()
        
        logger.info(f"[UPDATE_INCOME] Successfully updated entry {entry_id}")
        
        return jsonify({
            'success': True,
            'message': 'Income entry updated successfully',
            'income_entry_id': existing_entry.id
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"[UPDATE_INCOME] Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error updating income entry: {str(e)}'
        }), 500

@income_bp.route('/entries/<int:group_id>/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_income_entry_api(group_id, entry_id):
    """Delete an income entry"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Verify entry belongs to group
        entry = IncomeEntry.query.filter_by(id=entry_id, group_id=group_id).first()
        if not entry:
            return jsonify({
                'success': False,
                'message': 'Income entry not found in this group'
            }), 404
        
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Income entry deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting income entry: {e}")
        return jsonify({
            'success': False,
            'message': 'Error deleting income entry'
        }), 500

@income_bp.route('/categories/<int:group_id>', methods=['GET'])
@login_required
def get_income_categories_api(group_id):
    """Get all income categories for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get income categories for this group
        categories = IncomeCategory.query.filter_by(group_id=group_id).order_by(IncomeCategory.display_order.nullslast(), IncomeCategory.id).all()
        
        categories_data = []
        for category in categories:
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'group_id': category.group_id
            })
        
        return jsonify({
            'success': True,
            'income_categories': categories_data
        })
    
    except Exception as e:
        logger.error(f"Error getting income categories for group {group_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading income categories'
        }), 500