# app/routes/tracker/budgeting/api.py - API endpoints for budget data

from flask import jsonify, request
from flask_login import login_required, current_user
from models import Group
from app.services.tracker.budgeting import BudgetAnalyticsService
from datetime import date
from . import budgeting_bp
import logging

logger = logging.getLogger(__name__)

@budgeting_bp.route('/api/summary')
@login_required
def get_summary(group_id):
    """
    Get budget summary for specified period.
    Query params: year, months (comma-separated)
    """
    group = Group.query.get_or_404(group_id)
    
    # Check access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get parameters
    year = request.args.get('year', date.today().year, type=int)
    months_param = request.args.get('months', str(date.today().month))
    
    # Parse months
    try:
        if months_param:
            months = [int(m) for m in months_param.split(',')]
        else:
            months = [date.today().month]
    except ValueError:
        return jsonify({'error': 'Invalid months parameter'}), 400
    
    try:
        # Get summary for each month and combine
        summaries = []
        for month in months:
            summary = BudgetAnalyticsService.get_monthly_summary(
                group_id, current_user.id, year, month
            )
            if summary:
                summaries.append(summary)
        
        # Combine summaries
        combined = _combine_summaries(summaries)
        
        return jsonify({
            'success': True,
            'data': combined,
            'period': {
                'year': year,
                'months': months
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting budget summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgeting_bp.route('/api/category-breakdown')
@login_required
def get_category_breakdown(group_id):
    """
    Get detailed category breakdown with subcategories.
    Query params: year, month, category (optional)
    """
    group = Group.query.get_or_404(group_id)
    
    # Check access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get parameters
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    category_name = request.args.get('category', None)
    
    try:
        # Get full category analysis
        analysis = BudgetAnalyticsService.get_category_analysis(
            group_id, current_user.id, year, month
        )
        
        # If specific category requested, return just that
        if category_name and category_name in analysis:
            return jsonify({
                'success': True,
                'category': category_name,
                'data': analysis[category_name]
            })
        
        # Otherwise return all categories
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        logger.error(f"Error getting category breakdown: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@budgeting_bp.route('/api/recommendations')
@login_required  
def get_recommendations(group_id):
    """
    Get spending recommendations.
    Query params: year, month
    """
    group = Group.query.get_or_404(group_id)
    
    # Check access
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get parameters
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    try:
        recommendations = BudgetAnalyticsService.get_recommendations(
            group_id, current_user.id, year, month
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _combine_summaries(summaries):
    """Combine multiple monthly summaries into one"""
    if not summaries:
        return {
            'income': {'total': 0},
            'expenses': {'total': 0, 'essentials': 0, 'discretionary': 0, 'by_category': {}},
            'allocations': {'total_allocated': 0, 'by_budget_type': {}},
            'net_summary': {
                'total_income': 0,
                'total_expenses': 0,
                'net_cashflow': 0,
                'savings_rate': 0,
                'discretionary_left': 0
            }
        }
    
    if len(summaries) == 1:
        return summaries[0]
    
    # Combine multiple months
    combined = {
        'income': {'total': 0, 'by_category': {}},
        'expenses': {'total': 0, 'essentials': 0, 'discretionary': 0, 'by_category': {}, 'category_details': {}},
        'allocations': {'total_allocated': 0, 'by_budget_type': {}, 'by_category': {}},
        'net_summary': {}
    }
    
    for summary in summaries:
        # Income
        combined['income']['total'] += summary['income']['total']
        for cat, amount in summary['income'].get('by_category', {}).items():
            combined['income']['by_category'][cat] = combined['income']['by_category'].get(cat, 0) + amount
        
        # Expenses
        combined['expenses']['total'] += summary['expenses']['total']
        combined['expenses']['essentials'] += summary['expenses']['essentials']
        combined['expenses']['discretionary'] += summary['expenses']['discretionary']
        
        for cat, amount in summary['expenses'].get('by_category', {}).items():
            combined['expenses']['by_category'][cat] = combined['expenses']['by_category'].get(cat, 0) + amount
        
        for cat, details in summary['expenses'].get('category_details', {}).items():
            if cat not in combined['expenses']['category_details']:
                combined['expenses']['category_details'][cat] = {'total': 0, 'items': []}
            combined['expenses']['category_details'][cat]['total'] += details['total']
            combined['expenses']['category_details'][cat]['items'].extend(details.get('items', []))
        
        # Allocations
        combined['allocations']['total_allocated'] += summary['allocations']['total_allocated']
        
        for budget_type, amount in summary['allocations'].get('by_budget_type', {}).items():
            combined['allocations']['by_budget_type'][budget_type] = combined['allocations']['by_budget_type'].get(budget_type, 0) + amount
    
    # Calculate net summary
    total_income = combined['income']['total']
    total_expenses = combined['expenses']['total']
    net_cashflow = total_income - total_expenses
    
    combined['net_summary'] = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_cashflow': net_cashflow,
        'savings_rate': (net_cashflow / total_income * 100) if total_income > 0 else 0,
        'essential_ratio': (combined['expenses']['essentials'] / total_expenses * 100) if total_expenses > 0 else 0,
        'discretionary_left': total_income - combined['expenses']['essentials'] if total_income > 0 else 0
    }
    
    return combined