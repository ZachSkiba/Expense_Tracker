# models.py - FIXED: secrets.choices -> secrets.choice and other fixes

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func, Table
from dateutil.relativedelta import relativedelta
import json
import secrets
import string
import random  # Add this import as backup

db = SQLAlchemy()

# Association table for many-to-many relationship between users and groups
user_groups = Table('user_groups',
    db.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow),
    db.Column('role', db.String(20), default='member')  # 'admin', 'member'
)

class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    
    # User identification fields
    full_name = db.Column(db.String(100), nullable=False)  # Real full name (can be duplicate)
    display_name = db.Column(db.String(100), nullable=False)  # Display name (can be duplicate)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)  # Must be unique
    
    
    # Legacy authentication fields (nullable for backward compatibility)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for legacy users
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Original relationships (keep for backward compatibility)
    expenses = db.relationship("Expense", foreign_keys="Expense.user_id", back_populates="user")
    expense_participants = db.relationship("ExpenseParticipant", back_populates="user")
    balances = db.relationship("Balance", back_populates="user", cascade="all, delete-orphan")
    settlements_made = db.relationship("Settlement", foreign_keys="Settlement.payer_id", back_populates="payer")
    settlements_received = db.relationship("Settlement", foreign_keys="Settlement.receiver_id", back_populates="receiver")
    recurring_payments = db.relationship("RecurringPayment", back_populates="user")
    
    # New relationships for groups and personal categories
    groups = db.relationship('Group', 
                           secondary=user_groups, 
                           back_populates='members')
    owned_groups = db.relationship('Group', 
                                 foreign_keys='Group.creator_id',
                                 back_populates='creator')
    categories = db.relationship("Category", foreign_keys="Category.user_id", back_populates="user")

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_net_balance(self):
        """Calculate net balance for this user (legacy method)"""
        total_balance = db.session.query(func.sum(Balance.amount)).filter_by(user_id=self.id).scalar() or 0
        return float(total_balance)
    
    def get_group_balance(self, group_id=None):
        """Get balance within a specific group or all groups"""
        query = Balance.query.filter_by(user_id=self.id)
        if group_id:
            query = query.filter_by(group_id=group_id)
        
        total = query.with_entities(func.sum(Balance.amount)).scalar()
        return float(total or 0)
    
    def is_group_admin(self, group):
        """Check if user is admin of a group"""
        if isinstance(group, int):
            group_id = group
            # Get the group object to check creator
            group_obj = Group.query.get(group_id)
            if not group_obj:
                return False
        else:
            group_id = group.id
            group_obj = group
            
        # Check if user created the group
        if self.id == group_obj.creator_id:
            return True
            
        # Check association table for admin role
        association = db.session.execute(
            user_groups.select().where(
                user_groups.c.user_id == self.id,
                user_groups.c.group_id == group_id,
                user_groups.c.role == 'admin'
            )
        ).first()
        
        return association is not None
    
    def is_legacy_user(self):
        """Check if this is a legacy user (no email/username)"""
        return not self.email
    
    @property
    def name(self):
        """Backward compatibility property - returns display_name"""
        return self.display_name or self.full_name
    
    def __repr__(self):
        if hasattr(self, 'username') and self.username:
            return f'<User {self.username}>'
        else:
            return f'<User {self.display_name or self.full_name}>'


class Group(db.Model):
    __tablename__ = "group"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Group settings
    invite_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Who created this group
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', 
                            foreign_keys=[creator_id], 
                            back_populates='owned_groups')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = db.relationship('User', 
                            secondary=user_groups, 
                            back_populates='groups')
    
    expenses = db.relationship('Expense', back_populates='group', cascade="all, delete-orphan")
    recurring_payments = db.relationship('RecurringPayment', back_populates='group')
    categories = db.relationship('Category', foreign_keys='Category.group_id', back_populates='group')
    
    @staticmethod
    def generate_invite_code():
        """Generate a unique invite code - FIXED: secrets.choices -> secrets.choice"""        
        while True:
            try:
                # Use secrets.choice (correct method name)
                code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            except AttributeError:
                # Fallback for older Python versions
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            if not Group.query.filter_by(invite_code=code).first():
                return code
    
    def get_member_count(self):
        """Get number of members in this group"""
        return len(self.members)
    
    def add_member(self, user, role='member'):
        """Add a user to this group"""
        if user not in self.members:
            # Insert into association table with role
            stmt = user_groups.insert().values(
                user_id=user.id,
                group_id=self.id,
                role=role,
                joined_at=datetime.utcnow()
            )
            db.session.execute(stmt)
            return True
        return False
    
    def remove_member(self, user):
        """Remove a user from this group"""
        if user in self.members:
            stmt = user_groups.delete().where(
                user_groups.c.user_id == user.id,
                user_groups.c.group_id == self.id
            )
            db.session.execute(stmt)
            return True
        return False
    
    def __repr__(self):
        return f'<Group {self.name}>'


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    # Categories can be personal, group-specific, or default
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # For personal categories
    
    # Default categories (system-wide) - keep for backward compatibility
    is_default = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='category_user_unique'),
    )

    # Relationships
    group = db.relationship('Group', foreign_keys=[group_id], back_populates='categories')
    user = db.relationship('User', foreign_keys=[user_id], back_populates='categories')
    expenses = db.relationship("Expense", back_populates="category_obj")
    recurring_payments = db.relationship("RecurringPayment", back_populates="category_obj")

class Expense(db.Model):
    __tablename__ = "expense"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    
    # link to category table
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category_obj = db.relationship("Category", back_populates="expenses")
    category_description = db.Column(db.String(255), nullable=True)

    # link to user table (payer)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", foreign_keys=[user_id], back_populates="expenses")

    # Which group this expense belongs to (NULL for personal expenses)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    group = db.relationship("Group", back_populates="expenses")

    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Expense splitting
    split_type = db.Column(db.String(20), nullable=False, default='equal')  # 'equal', 'custom', 'personal'
    
    # Recurring payment tracking
    recurring_payment_id = db.Column(db.Integer, db.ForeignKey("recurring_payment.id"), nullable=True)
    recurring_payment = db.relationship('RecurringPayment', back_populates='created_expenses')
    
    # relationship to participants
    participants = db.relationship("ExpenseParticipant", back_populates="expense", cascade="all, delete-orphan")
    
    def is_personal(self):
        """Check if this is a personal expense"""
        return self.group_id is None
    
    def is_group_expense(self):
        """Check if this is a group expense"""
        return self.group_id is not None

# FIXED: Add group_id to ExpenseParticipant table
class ExpenseParticipant(db.Model):
    """Track who participated in each expense and their share"""
    __tablename__ = "expense_participant"

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expense.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # ADDED: Group context for easier querying
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    
    amount_owed = db.Column(db.Float, nullable=False)  # How much this participant owes for this expense
    
    # relationships
    expense = db.relationship("Expense", back_populates="participants")
    user = db.relationship("User", back_populates="expense_participants")
    group = db.relationship("Group")  # Add group relationship

class Balance(db.Model):
    """Track running balances between users"""
    __tablename__ = "balance"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Group context for the balance (NULL for legacy/personal balances)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    
    amount = db.Column(db.Float, nullable=False, default=0.0)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # relationship to user and group
    user = db.relationship("User", back_populates="balances")
    group = db.relationship("Group")

class Settlement(db.Model):
    """Track settlements/payments between users"""
    __tablename__ = "settlement"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    
    # Who paid whom
    payer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Group context (nullable for personal settlements)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    
    # When and optional description
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # relationships
    payer = db.relationship("User", foreign_keys=[payer_id], back_populates="settlements_made")
    receiver = db.relationship("User", foreign_keys=[receiver_id], back_populates="settlements_received")
    group = db.relationship("Group")
    
    def __repr__(self):
        return f'<Settlement {self.payer.name} -> {self.receiver.name}: ${self.amount}>'


class RecurringPayment(db.Model):
    __tablename__ = "recurring_payment"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    
    # Category and description
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category_obj = db.relationship("Category", back_populates="recurring_payments")
    category_description = db.Column(db.String(255), nullable=True)
    
    # Who pays
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="recurring_payments")
    
    # Group context (nullable for personal recurring payments)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    group = db.relationship("Group", back_populates="recurring_payments")
    
    # Recurrence settings
    frequency = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly', 'custom'
    interval_value = db.Column(db.Integer, nullable=False, default=1)  # e.g., every 2 weeks = interval_value=2, frequency='weekly'
    
    # Dates
    start_date = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # Optional end date
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Participants (who splits this recurring payment)
    participant_ids = db.Column(db.Text, nullable=False)  # JSON string of user IDs
    
    # Relationship to generated expenses - FIXED
    created_expenses = db.relationship("Expense", back_populates="recurring_payment")
    
    def get_participant_ids(self):
        return json.loads(self.participant_ids) if self.participant_ids else []
    
    def set_participant_ids(self, ids_list):
        self.participant_ids = json.dumps(ids_list)
    
    def calculate_next_due_date(self, from_date=None):
        if from_date is None:
            from_date = self.next_due_date
        
        if self.frequency == 'daily':
            return from_date + timedelta(days=self.interval_value)
        elif self.frequency == 'weekly':
            return from_date + timedelta(weeks=self.interval_value)
        elif self.frequency == 'monthly':
            return from_date + relativedelta(months=self.interval_value)
        elif self.frequency == 'yearly':
            return from_date + relativedelta(years=self.interval_value)
        else:
            # Default to monthly if unknown frequency
            return from_date + relativedelta(months=self.interval_value)
    
    def is_due(self, check_date=None):
        if not self.is_active:
            return False
            
        if check_date is None:
            check_date = datetime.now().date()
            
        if self.end_date and check_date > self.end_date:
            return False
            
        return check_date >= self.next_due_date
    
    def is_personal(self):
        """Check if this is a personal recurring payment"""
        return self.group_id is None
    
    def __repr__(self):
        return f'<RecurringPayment {self.category_obj.name}: ${self.amount} every {self.interval_value} {self.frequency}>'