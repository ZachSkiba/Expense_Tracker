# app/routes/tracker/budgeting/analytics.py - Main budget analytics route

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Group
from datetime import date
from . import budgeting_bp

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
    
    # Only show budget analytics for personal trackers
    if not group.is_personal_tracker:
        flash('Budget analytics is only available for personal trackers', 'info')
        return redirect(url_for('expenses.group_tracker', group_id=group_id))
    
    # Get current date for default filters
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    # Get filter parameters from query string (optional)
    selected_year = request.args.get('year', current_year, type=int)
    selected_months = request.args.getlist('months', type=int)
    
    # If no months selected, default to current month
    if not selected_months:
        selected_months = [current_month]
    
    return render_template(
        'tracker/budgeting/analytics.html',
        group=group,
        current_year=current_year,
        current_month=current_month,
        selected_year=selected_year,
        selected_months=selected_months,
        user=current_user
    )