# models/budget_preferences.py - User budget preferences per group

from models import db
from datetime import datetime

class BudgetPreference(db.Model):
    """
    Stores user budget preferences for the 50/30/20 rule customization.
    One record per user per group (personal tracker).
    """
    __tablename__ = "budget_preference"

    id = db.Column(db.Integer, primary_key=True)
    
    # User and Group context
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', backref='budget_preferences')
    
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    group = db.relationship('Group')
    
    # Custom percentages (must add up to 100)
    needs_percent = db.Column(db.Float, default=50.0, nullable=False)
    wants_percent = db.Column(db.Float, default=30.0, nullable=False)
    savings_percent = db.Column(db.Float, default=20.0, nullable=False)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'group_id', name='unique_user_group_budget_pref'),
    )
    
    def validate_percentages(self):
        """Validate that percentages add up to 100"""
        total = self.needs_percent + self.wants_percent + self.savings_percent
        return abs(total - 100.0) < 0.01  # Allow for floating point rounding
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'needs_percent': self.needs_percent,
            'wants_percent': self.wants_percent,
            'savings_percent': self.savings_percent
        }
    
    @staticmethod
    def get_or_create_default(user_id, group_id):
        """Get existing preference or create default 50/30/20"""
        pref = BudgetPreference.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()
        
        if not pref:
            pref = BudgetPreference(
                user_id=user_id,
                group_id=group_id,
                needs_percent=50.0,
                wants_percent=30.0,
                savings_percent=20.0
            )
            db.session.add(pref)
            db.session.commit()
        
        return pref
    
    def reset_to_default(self):
        """Reset to 50/30/20 rule"""
        self.needs_percent = 50.0
        self.wants_percent = 30.0
        self.savings_percent = 20.0
    
    def __repr__(self):
        return f'<BudgetPreference User:{self.user_id} Group:{self.group_id} {self.needs_percent}/{self.wants_percent}/{self.savings_percent}>'