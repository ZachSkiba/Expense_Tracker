# app/routes/dashboard.py - Main dashboard routes (cleaned and split)

from flask import Blueprint, request, redirect, url_for, render_template_string, flash
from flask_login import login_required, current_user
from models import User, Expense, Category, db
from sqlalchemy import func, desc
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def home():
    """Main dashboard showing personal and group expenses"""
    
    # Get user's recent personal expenses
    personal_expenses = Expense.query.filter_by(
        user_id=current_user.id,
        group_id=None
    ).order_by(desc(Expense.date)).limit(5).all()
    
    # Get user's groups
    user_groups = current_user.groups
    
    # Get recent group activities
    group_activities = []
    if user_groups:
        group_ids = [g.id for g in user_groups]
        recent_group_expenses = Expense.query.filter(
            Expense.group_id.in_(group_ids)
        ).order_by(desc(Expense.date)).limit(10).all()
        
        for expense in recent_group_expenses:
            group_activities.append({
                'type': 'expense',
                'expense': expense,
                'group': expense.group,
                'user': expense.user
            })
    
    # Calculate personal spending this month
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    personal_monthly_total = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.group_id == None,
        Expense.date >= start_of_month.date()
    ).scalar() or 0
    
    # Get group balances
    group_balances = {}
    for group in user_groups:
        balance = current_user.get_group_balance(group.id)
        group_balances[group.id] = balance
    
    # Import template function
    from app.templates.groups.dashboard_templates import get_dashboard_template
    
    return render_template_string(
        get_dashboard_template(),
        user=current_user,
        personal_expenses=personal_expenses,
        user_groups=user_groups,
        group_activities=group_activities,
        personal_monthly_total=personal_monthly_total,
        group_balances=group_balances
    )