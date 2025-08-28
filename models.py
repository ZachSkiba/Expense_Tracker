from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

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