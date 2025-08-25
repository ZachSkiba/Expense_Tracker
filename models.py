from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # relationship to expenses
    expenses = db.relationship("Expense", back_populates="user")

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

    # link to user table
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="expenses")

    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
