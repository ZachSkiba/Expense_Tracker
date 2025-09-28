# Import the main db instance and base models
from .models import *
from .income_models import *

# Make sure all models are available when importing from models
__all__ = [
    'db', 'User', 'Group', 'Category', 'Expense', 'ExpenseParticipant',
    'Balance', 'Settlement', 'RecurringPayment', 'user_groups',
    'IncomeCategory', 'IncomeEntry',
]