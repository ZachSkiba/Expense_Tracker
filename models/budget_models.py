# models/budget_models.py - Budget analytics models (SIMPLIFIED)

from models import db
from datetime import datetime, date
import json
from sqlalchemy import and_

class BudgetCategory(db.Model):
    """
    Maps existing expense/income categories to budget types with intelligent rules.
    Enables automatic categorization and smart allocation recommendations.
    """
    __tablename__ = "budget_category"

    id = db.Column(db.Integer, primary_key=True)
    
    # Link to existing expense category (nullable - can be expense OR allocation)
    expense_category_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'), nullable=True)
    expense_category = db.relationship('Category', foreign_keys=[expense_category_id])
    
    # Link to income allocation category (nullable - can be expense OR allocation)
    allocation_category_id = db.Column(db.Integer, db.ForeignKey('income_allocation_category.id', ondelete='SET NULL'), nullable=True)
    allocation_category = db.relationship('IncomeAllocationCategory', foreign_keys=[allocation_category_id])
    
    # Budget classification
    budget_type = db.Column(db.String(50), nullable=False)
    
    # Group context (required)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    group = db.relationship('Group')
    
    # Smart allocation rules stored as JSON
    allocation_rules = db.Column(db.Text, nullable=True)
    
    # Historical averages (calculated automatically by analytics engine)
    avg_monthly_amount = db.Column(db.Float, default=0)
    last_calculated = db.Column(db.DateTime, nullable=True)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_allocation_rules(self):
        """Parse JSON allocation rules"""
        if self.allocation_rules:
            try:
                return json.loads(self.allocation_rules)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_allocation_rules(self, rules_dict):
        """Set allocation rules from dictionary"""
        if rules_dict:
            self.allocation_rules = json.dumps(rules_dict)
        else:
            self.allocation_rules = None
    
    def get_recommended_percent(self):
        """Get recommended allocation percentage"""
        rules = self.get_allocation_rules()
        return rules.get('recommended_percent', 0)
    
    def get_category_name(self):
        """Get the name of the linked category"""
        if self.expense_category:
            return self.expense_category.name
        elif self.allocation_category:
            return self.allocation_category.name
        return "Unknown"
    
    def is_expense_category(self):
        """Check if this maps to an expense category"""
        return self.expense_category_id is not None
    
    def is_allocation_category(self):
        """Check if this maps to an allocation category"""
        return self.allocation_category_id is not None
    
    def __repr__(self):
        category_name = self.get_category_name()
        return f'<BudgetCategory {category_name} -> {self.budget_type}>'


class BudgetSnapshot(db.Model):
    """
    Monthly snapshots for trend analysis, forecasting, and time-series analytics.
    """
    __tablename__ = "budget_snapshot"

    id = db.Column(db.Integer, primary_key=True)
    
    # Context
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    group = db.relationship('Group')
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User')
    
    # Time period (stored as first day of month for consistency)
    snapshot_date = db.Column(db.Date, nullable=False)
    
    # Aggregated financial metrics
    total_income = db.Column(db.Float, default=0)
    total_expenses = db.Column(db.Float, default=0)
    total_essentials = db.Column(db.Float, default=0)
    total_discretionary = db.Column(db.Float, default=0)
    
    # Detailed breakdowns stored as JSON
    allocation_breakdown = db.Column(db.Text, nullable=True)
    category_breakdown = db.Column(db.Text, nullable=True)
    
    # Data science metrics
    savings_rate = db.Column(db.Float, default=0)
    expense_variance = db.Column(db.Float, default=0)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', 'snapshot_date', name='unique_snapshot'),
    )
    
    def get_allocation_breakdown(self):
        """Parse JSON allocation breakdown"""
        if self.allocation_breakdown:
            try:
                return json.loads(self.allocation_breakdown)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_allocation_breakdown(self, breakdown_dict):
        """Set allocation breakdown from dictionary"""
        if breakdown_dict:
            self.allocation_breakdown = json.dumps(breakdown_dict)
        else:
            self.allocation_breakdown = None
    
    def get_category_breakdown(self):
        """Parse JSON category breakdown"""
        if self.category_breakdown:
            try:
                return json.loads(self.category_breakdown)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_category_breakdown(self, breakdown_dict):
        """Set category breakdown from dictionary"""
        if breakdown_dict:
            self.category_breakdown = json.dumps(breakdown_dict)
        else:
            self.category_breakdown = None
    
    def calculate_savings_rate(self):
        """Calculate savings rate as percentage of income"""
        if self.total_income > 0:
            savings = self.total_income - self.total_expenses
            self.savings_rate = (savings / self.total_income) * 100
        else:
            self.savings_rate = 0
        return self.savings_rate
    
    def get_discretionary_spending(self):
        """Calculate discretionary spending (non-essential)"""
        return self.total_expenses - self.total_essentials
    
    def get_essential_ratio(self):
        """Get percentage of expenses that are essential"""
        if self.total_expenses > 0:
            return (self.total_essentials / self.total_expenses) * 100
        return 0
    
    @staticmethod
    def get_or_create_for_month(group_id, user_id, year, month):
        """Get or create a snapshot for a specific month"""
        snapshot_date = date(year, month, 1)
        
        existing = BudgetSnapshot.query.filter_by(
            group_id=group_id,
            user_id=user_id,
            snapshot_date=snapshot_date
        ).first()
        
        if existing:
            return existing
        
        new_snapshot = BudgetSnapshot(
            group_id=group_id,
            user_id=user_id,
            snapshot_date=snapshot_date
        )
        
        db.session.add(new_snapshot)
        return new_snapshot
    
    @staticmethod
    def get_snapshots_for_period(group_id, user_id, start_date, end_date):
        """Get all snapshots for a user within a date range"""
        return BudgetSnapshot.query.filter(
            and_(
                BudgetSnapshot.group_id == group_id,
                BudgetSnapshot.user_id == user_id,
                BudgetSnapshot.snapshot_date >= start_date,
                BudgetSnapshot.snapshot_date <= end_date
            )
        ).order_by(BudgetSnapshot.snapshot_date).all()
    
    @staticmethod
    def get_last_n_months(group_id, user_id, n=6):
        """Get snapshots for the last N months"""
        return BudgetSnapshot.query.filter_by(
            group_id=group_id,
            user_id=user_id
        ).order_by(BudgetSnapshot.snapshot_date.desc()).limit(n).all()
    
    def __repr__(self):
        return f'<BudgetSnapshot {self.user.name} - {self.snapshot_date.strftime("%Y-%m")}>'