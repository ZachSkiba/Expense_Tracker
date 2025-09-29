# app/services/tracker/income_allocation.py - Income allocation API endpoints

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Group
from models.income_models import IncomeEntry, IncomeAllocationCategory, IncomeAllocation
import logging

# Set up logging
logger = logging.getLogger(__name__)

income_allocation_bp = Blueprint('income_allocation', __name__, url_prefix='/api/income/allocation')

@income_allocation_bp.route('/categories/<int:group_id>', methods=['GET'])
@login_required
def get_income_allocation_categories_api(group_id):
    """Get all income allocation categories for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get income allocation categories for this group
        # Get income allocation categories for this group
        categories = IncomeAllocationCategory.query.filter_by(group_id=group_id).order_by(IncomeAllocationCategory.name).all()

        # Create default allocation categories if none exist
        if not categories:
            try:
                created_defaults = IncomeAllocationCategory.create_default_categories(group_id)
                if created_defaults:
                    db.session.commit()
                    categories = IncomeAllocationCategory.query.filter_by(group_id=group_id).order_by(IncomeAllocationCategory.name).all()
                    logger.info(f"Created {len(created_defaults)} default income allocation categories for group {group_id}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating default allocation categories for group {group_id}: {e}")
        
        categories_data = []
        for category in categories:
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'group_id': category.group_id
            })
        
        return jsonify({
            'success': True,
            'allocation_categories': categories_data
        })
    
    except Exception as e:
        logger.error(f"Error getting income allocation categories for group {group_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading income allocation categories'
        }), 500

@income_allocation_bp.route('/entries/<int:group_id>/<int:income_entry_id>', methods=['GET'])
@login_required
def get_income_allocations_api(group_id, income_entry_id):
    """Get all allocations for a specific income entry"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Verify income entry belongs to group
        income_entry = IncomeEntry.query.filter_by(id=income_entry_id, group_id=group_id).first()
        if not income_entry:
            return jsonify({
                'success': False,
                'message': 'Income entry not found in this group'
            }), 404
        
        # Get allocations for this income entry
        allocations = IncomeAllocation.query.filter_by(income_entry_id=income_entry_id).all()
        
        allocations_data = []
        for allocation in allocations:
            allocations_data.append({
                'id': allocation.id,
                'amount': allocation.amount,
                'allocation_category_id': allocation.allocation_category_id,
                'allocation_category_name': allocation.allocation_category_obj.name,
                'notes': allocation.notes,
                'income_entry_id': allocation.income_entry_id,
                'created_at': allocation.created_at.isoformat(),
                'updated_at': allocation.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'allocations': allocations_data,
            'income_entry': {
                'id': income_entry.id,
                'amount': income_entry.amount,
                'description': income_entry.description,
                'date': income_entry.date.isoformat(),
                'user_name': income_entry.user.name,
                'category_name': income_entry.income_category_obj.name,
                # Add these additional fields that JavaScript expects
                'income_category_name': income_entry.income_category_obj.name,
                'user_id': income_entry.user_id,
                'income_category_id': income_entry.income_category_id
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting allocations for income entry {income_entry_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading income allocations'
        }), 500

@income_allocation_bp.route('/entries/<int:group_id>/<int:income_entry_id>', methods=['POST'])
@login_required
def save_income_allocations_api(group_id, income_entry_id):
    """Save multiple allocations for an income entry (replaces existing allocations)"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.json
        logger.info(f"[SAVE_ALLOCATIONS] Received data for income entry {income_entry_id}: {data}")
        
        # Verify income entry belongs to group
        income_entry = IncomeEntry.query.filter_by(id=income_entry_id, group_id=group_id).first()
        if not income_entry:
            return jsonify({
                'success': False,
                'message': 'Income entry not found in this group'
            }), 404
        
        # Validate allocations data
        allocations_data = data.get('allocations', [])
        if not allocations_data:
            return jsonify({
                'success': False,
                'message': 'No allocation data provided'
            }), 400
        
        # Validate each allocation
        total_allocated = 0
        for allocation in allocations_data:
            if not all(key in allocation for key in ['allocation_category_id', 'amount']):
                return jsonify({
                    'success': False,
                    'message': 'Missing required allocation fields'
                }), 400
            
            try:
                amount = float(allocation['amount'])
                if amount <= 0:
                    raise ValueError("Amount must be positive")
                total_allocated += amount
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Invalid allocation amount'
                }), 400
            
            # Verify category exists and belongs to group
            category = IncomeAllocationCategory.query.filter_by(
                id=allocation['allocation_category_id'], 
                group_id=group_id
            ).first()
            if not category:
                return jsonify({
                    'success': False,
                    'message': 'Invalid allocation category'
                }), 400
        
        # Validate total doesn't exceed income entry amount
        if total_allocated > income_entry.amount:
            return jsonify({
                'success': False,
                'message': f'Total allocated (${total_allocated:.2f}) exceeds income amount (${income_entry.amount:.2f})'
            }), 400
        
        # Delete existing allocations for this income entry
        IncomeAllocation.query.filter_by(income_entry_id=income_entry_id).delete()
        
        # Create new allocations
        created_allocations = []
        for allocation_data in allocations_data:
            allocation = IncomeAllocation(
                amount=float(allocation_data['amount']),
                allocation_category_id=int(allocation_data['allocation_category_id']),
                notes=allocation_data.get('notes', '').strip() or None,
                income_entry_id=income_entry_id
            )
            db.session.add(allocation)
            created_allocations.append(allocation)
        
        db.session.commit()
        
        logger.info(f"[SAVE_ALLOCATIONS] Created {len(created_allocations)} allocations for income entry {income_entry_id}")
        
        return jsonify({
            'success': True,
            'message': f'Saved {len(created_allocations)} allocation(s) successfully',
            'allocations_count': len(created_allocations),
            'total_allocated': total_allocated,
            'remaining_unallocated': income_entry.amount - total_allocated
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"[SAVE_ALLOCATIONS] Error saving allocations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error saving allocations'
        }), 500

@income_allocation_bp.route('/entries/<int:group_id>/<int:income_entry_id>/<int:allocation_id>', methods=['DELETE'])
@login_required
def delete_income_allocation_api(group_id, income_entry_id, allocation_id):
    """Delete a specific allocation"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Verify allocation exists and belongs to the income entry
        allocation = IncomeAllocation.query.filter_by(
            id=allocation_id,
            income_entry_id=income_entry_id
        ).first()
        
        if not allocation:
            return jsonify({
                'success': False,
                'message': 'Allocation not found'
            }), 404
        
        # Verify income entry belongs to group
        if allocation.income_entry.group_id != group_id:
            return jsonify({
                'success': False,
                'message': 'Allocation not found in this group'
            }), 404
        
        db.session.delete(allocation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Allocation deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting allocation: {e}")
        return jsonify({
            'success': False,
            'message': 'Error deleting allocation'
        }), 500
    

# Management routes for income allocation categories
@income_allocation_bp.route('/categories/<int:group_id>', methods=['POST'])
@login_required
def add_income_allocation_category_api(group_id):
    """Add new income allocation category"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        category_name = data.get('name', '').strip()
        
        if not category_name:
            return jsonify({'success': False, 'message': 'Category name is required'})
        
        # Check if category already exists for this group
        existing = IncomeAllocationCategory.query.filter_by(name=category_name, group_id=group_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Category already exists'})
        
        # Create new category
        new_category = IncomeAllocationCategory(
            name=category_name,
            group_id=group_id
        )
        
        db.session.add(new_category)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Income allocation category added successfully',
            'category': {
                'id': new_category.id,
                'name': new_category.name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding income allocation category: {e}")
        return jsonify({'success': False, 'message': 'Error adding category'}), 500

@income_allocation_bp.route('/categories/<int:group_id>/<int:category_id>', methods=['DELETE'])
@login_required
def delete_income_allocation_category_api(group_id, category_id):
    """Delete income allocation category"""
    group = Group.query.get_or_404(group_id)
    
    # Check user access
    if current_user not in group.members:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Find category
        category = IncomeAllocationCategory.query.filter_by(id=category_id, group_id=group_id).first()
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'})
        
        # Check if category is being used
        from models.income_models import IncomeAllocation
        allocation_count = IncomeAllocation.query.filter_by(allocation_category_id=category_id).count()
        
        if allocation_count > 0:
            return jsonify({
                'success': False, 
                'message': f'Cannot delete category. It is used in {allocation_count} allocation(s).'
            })
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Income allocation category deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting income allocation category: {e}")
        return jsonify({'success': False, 'message': 'Error deleting category'}), 500