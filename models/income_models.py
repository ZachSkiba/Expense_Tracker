# models/income_models.py - Income tracking models

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from models import db

class IncomeCategory(db.Model):
    """Categories for income sources (e.g., Employer, Freelance, Investments)"""
    __tablename__ = "income_category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    # Group-specific categories (same pattern as expense categories)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # For personal categories
    
    # Default categories (system-wide) - for backward compatibility
    is_default = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('name', 'group_id', name='income_category_group_unique'),
    )

    # Relationships
    group = db.relationship('Group', foreign_keys=[group_id])
    user = db.relationship('User', foreign_keys=[user_id])
    income_entries = db.relationship("IncomeEntry", back_populates="income_category_obj")

    def __repr__(self):
        return f'<IncomeCategory {self.name}>'


class IncomeEntry(db.Model):
    """Individual income entries"""
    __tablename__ = "income_entry"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    
    # Link to income category
    income_category_id = db.Column(db.Integer, db.ForeignKey("income_category.id"), nullable=False)
    income_category_obj = db.relationship("IncomeCategory", back_populates="income_entries")
    
    # Optional description
    description = db.Column(db.String(255), nullable=True)
    
    # Who received this income
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", foreign_keys=[user_id])
    
    # Which group this income belongs to (for personal trackers)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    group = db.relationship("Group")
    allocations = db.relationship("IncomeAllocation", back_populates="income_entry", cascade="all, delete-orphan")
    
    # Date received
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_personal(self):
        """Check if this is a personal income entry"""
        return self.group_id is not None
    
    def __repr__(self):
        return f'<IncomeEntry ${self.amount} from {self.income_category_obj.name}>'
    
class IncomeAllocationCategory(db.Model):
    """Categories for income allocations (e.g., Checking Account, Savings, 401k, Roth IRA)"""
    __tablename__ = "income_allocation_category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    # Group-specific allocation categories
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # For personal categories
    
    # Default categories (system-wide)
    is_default = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('name', 'group_id', name='income_allocation_category_group_unique'),
    )

    # Relationships
    group = db.relationship('Group', foreign_keys=[group_id])
    user = db.relationship('User', foreign_keys=[user_id])
    allocations = db.relationship("IncomeAllocation", back_populates="allocation_category_obj")

    def __repr__(self):
        return f'<IncomeAllocationCategory {self.name}>'


class IncomeAllocation(db.Model):
    """Individual allocations for income entries"""
    __tablename__ = "income_allocation"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    
    # Link to income entry
    income_entry_id = db.Column(db.Integer, db.ForeignKey("income_entry.id"), nullable=False)
    income_entry = db.relationship("IncomeEntry", back_populates="allocations")
    
    # Link to allocation category
    allocation_category_id = db.Column(db.Integer, db.ForeignKey("income_allocation_category.id"), nullable=False)
    allocation_category_obj = db.relationship("IncomeAllocationCategory", back_populates="allocations")
    
    # Optional notes for this specific allocation
    notes = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<IncomeAllocation ${self.amount} to {self.allocation_category_obj.name}>'