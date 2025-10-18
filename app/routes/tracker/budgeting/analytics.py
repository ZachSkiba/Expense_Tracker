# app/routes/tracker/budgeting/analytics.py - Main budget analytics route

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Group, Expense, ExpenseParticipant  # Add Expense, ExpenseParticipant
from models.income_models import IncomeEntry  # Add this
from datetime import date
from sqlalchemy import extract, func  # Add this
from . import budgeting_bp
from models import db

@budgeting_bp.route('/analytics')
@login_required
def analytics(group_id):
    """
    Budget analytics dashboard - shows financial overview and breakdowns.
    Only available for personal trackers.
    """
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('dashboard.home'))
    
    # Budget analytics available for all groups
    # Personal trackers: Full analytics with income
    # Group trackers: Expense analytics only (no income features)
    
    # Get current date for default filters
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    # Get filter parameters from query string (optional)
    selected_year = request.args.get('year', current_year, type=int)
    selected_months_param = request.args.getlist('months', type=int)
    
    # If no months selected, default to current month
    if not selected_months_param:
        selected_months = [current_month]
    else:
        selected_months = selected_months_param
    
    # Convert to JSON for JavaScript
    import json
    selected_months_json = json.dumps(selected_months)
    
    return render_template(
        'tracker/budgeting/analytics.html',
        group=group,
        current_year=current_year,
        current_month=current_month,
        selected_year=selected_year,
        selected_months=selected_months_json,
        user=current_user,
        is_personal_tracker=group.is_personal_tracker
    )

@budgeting_bp.route('/api/available-periods')
@login_required
def get_available_periods(group_id):
    """
    Get available years and months that have data for this user.
    Returns only periods where expenses or income exist.
    
    Query params:
        years (optional): Comma-separated list of years to filter months
    """
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if current_user not in group.members:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get optional years filter
    years_param = request.args.get('years', None)
    selected_years = None
    if years_param:
        try:
            selected_years = [int(y) for y in years_param.split(',')]
        except ValueError:
            pass
    
    try:
        # Build base queries
        expense_query = db.session.query(
            extract('year', Expense.date).label('year'),
            extract('month', Expense.date).label('month')
        ).join(ExpenseParticipant).filter(
            Expense.group_id == group_id,
            ExpenseParticipant.user_id == current_user.id
        )
        
        income_query = db.session.query(
            extract('year', IncomeEntry.date).label('year'),
            extract('month', IncomeEntry.date).label('month')
        ).filter(
            IncomeEntry.group_id == group_id,
            IncomeEntry.user_id == current_user.id
        )
        
        # Apply year filter if provided (for months)
        if selected_years:
            expense_query = expense_query.filter(extract('year', Expense.date).in_(selected_years))
            income_query = income_query.filter(extract('year', IncomeEntry.date).in_(selected_years))
        
        expense_dates = expense_query.distinct().all()
        income_dates = income_query.distinct().all()
        
        # Combine and deduplicate
        all_dates = set(expense_dates + income_dates)
        
        # Extract unique years and months
        years = sorted(set(int(d.year) for d in all_dates), reverse=True)
        months = sorted(set(int(d.month) for d in all_dates))
        
        # If no data, default to current year/month
        if not years:
            years = [date.today().year]
        if not months:
            months = [date.today().month]
        
        return jsonify({
            'success': True,
            'data': {
                'years': years,
                'months': months
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500