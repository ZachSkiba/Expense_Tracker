from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
from dateutil.relativedelta import relativedelta

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # relationship to expenses (as payer)
    expenses = db.relationship("Expense", back_populates="user")
    
    # relationship to expense participants
    expense_participants = db.relationship("ExpenseParticipant", back_populates="user")
    
    # relationship to balances
    balances = db.relationship("Balance", back_populates="user", cascade="all, delete-orphan")
    
    # relationship to settlements (as payer and receiver)
    settlements_made = db.relationship("Settlement", foreign_keys="Settlement.payer_id", back_populates="payer")
    settlements_received = db.relationship("Settlement", foreign_keys="Settlement.receiver_id", back_populates="receiver")
    
    # relationship to recurring payments (as payer)
    recurring_payments = db.relationship("RecurringPayment", back_populates="user")

    def get_net_balance(self):
        """Calculate net balance for this user"""
        total_balance = db.session.query(func.sum(Balance.amount)).filter_by(user_id=self.id).scalar() or 0
        return float(total_balance)

class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # relationship to expenses
    expenses = db.relationship("Expense", back_populates="category_obj")
    
    # relationship to recurring payments
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
    user = db.relationship("User", back_populates="expenses")

    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # New fields
    split_type = db.Column(db.String(20), nullable=False, default='equal')  # 'equal', 'custom'
    
    # Link to recurring payment if this expense was auto-generated
    recurring_payment_id = db.Column(db.Integer, db.ForeignKey("recurring_payment.id"), nullable=True)
    recurring_payment = db.relationship("RecurringPayment", back_populates="generated_expenses")
    recurring_payment = db.relationship('RecurringPayment', backref='created_expenses')
    
    # relationship to participants
    participants = db.relationship("ExpenseParticipant", back_populates="expense", cascade="all, delete-orphan")

class ExpenseParticipant(db.Model):
    """Track who participated in each expense and their share"""
    __tablename__ = "expense_participant"

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expense.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount_owed = db.Column(db.Float, nullable=False)  # How much this participant owes for this expense
    
    # relationships
    expense = db.relationship("Expense", back_populates="participants")
    user = db.relationship("User", back_populates="expense_participants")

class Balance(db.Model):
    """Track running balances between users"""
    __tablename__ = "balance"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("user.id", ondelete="CASCADE"),  # <-- add ondelete
        nullable=False
    )
    amount = db.Column(db.Float, nullable=False, default=0.0)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # relationship to user
    user = db.relationship("User", back_populates="balances")

class Settlement(db.Model):
    """Track settlements/payments between users"""
    __tablename__ = "settlement"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    
    # Who paid whom
    payer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # When and optional description
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # relationships
    payer = db.relationship("User", foreign_keys=[payer_id], back_populates="settlements_made")
    receiver = db.relationship("User", foreign_keys=[receiver_id], back_populates="settlements_received")
    
    def __repr__(self):
        return f'<Settlement {self.payer.name} -> {self.receiver.name}: ${self.amount}>'

class RecurringPayment(db.Model):
    """Track recurring payments like rent, utilities, subscriptions"""
    __tablename__ = "recurring_payment"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Monthly Rent", "Netflix Subscription"
    amount = db.Column(db.Float, nullable=False)
    
    # Category and description
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category_obj = db.relationship("Category", back_populates="recurring_payments")
    category_description = db.Column(db.String(255), nullable=True)
    
    # Who pays
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="recurring_payments")
    
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
    
    # Relationship to generated expenses
    generated_expenses = db.relationship("Expense", back_populates="recurring_payment")
    
    def get_participant_ids(self):
        """Get list of participant user IDs"""
        import json
        return json.loads(self.participant_ids) if self.participant_ids else []
    
    def set_participant_ids(self, ids_list):
        """Set participant user IDs"""
        import json
        self.participant_ids = json.dumps(ids_list)
    
    def calculate_next_due_date(self, from_date=None):
        """Calculate the next due date based on frequency and interval"""
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
        """Check if this recurring payment is due"""
        if not self.is_active:
            return False
            
        if check_date is None:
            check_date = datetime.now().date()
            
        if self.end_date and check_date > self.end_date:
            return False
            
        return check_date >= self.next_due_date
    
    def __repr__(self):
        return f'<RecurringPayment {self.name}: ${self.amount} every {self.interval_value} {self.frequency}>'