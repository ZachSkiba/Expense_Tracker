
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from models import db

# Budget categories map to existing expense/income categories
# with additional metadata for budgeting rules

class BudgetCategory(db.Model):
    """
    Maps existing categories to budget types with intelligent rules.
    This enables automatic categorization and smart recommendations.
    """
    __tablename__ = "budget_category"
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to existing expense category
    expense_category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    expense_category = db.relationship('Category')
    
    # Or link to income allocation category  
    allocation_category_id = db.Column(db.Integer, db.ForeignKey('income_allocation_category.id'), nullable=True)
    allocation_category = db.relationship('IncomeAllocationCategory')
    
    # Budget classification
    budget_type = db.Column(db.String(50), nullable=False)  
    # 'essential', 'investment', 'emergency', 'personal', 'debt'
    
    # Group context
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    group = db.relationship('Group')
    
    # Smart allocation rules (stored as JSON)
    allocation_rules = db.Column(db.Text, nullable=True)  
    # e.g., {"min_percent": 5, "max_percent": 30, "recommended_percent": 20}
    
    # Historical averages (updated automatically)
    avg_monthly_amount = db.Column(db.Float, default=0)
    last_calculated = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BudgetSnapshot(db.Model):
    """
    Monthly snapshots for trend analysis and forecasting.
    Enables time-series analysis and pattern recognition.
    """
    __tablename__ = "budget_snapshot"
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Time period
    snapshot_date = db.Column(db.Date, nullable=False)  # First day of month
    
    # Aggregated metrics
    total_income = db.Column(db.Float, default=0)
    total_expenses = db.Column(db.Float, default=0)
    total_essentials = db.Column(db.Float, default=0)
    total_discretionary = db.Column(db.Float, default=0)
    
    # Allocation breakdown (JSON)
    allocation_breakdown = db.Column(db.Text, nullable=True)
    # {"investments": 480, "emergency": 240, "personal": 360, "debt": 120}
    
    # Category breakdown (JSON)
    category_breakdown = db.Column(db.Text, nullable=True)
    # {"Groceries": 420, "Transportation": 350, ...}
    
    # Metrics for data science
    savings_rate = db.Column(db.Float, default=0)  # Percentage
    expense_variance = db.Column(db.Float, default=0)  # vs. previous month
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', 'snapshot_date', name='unique_snapshot'),
    )