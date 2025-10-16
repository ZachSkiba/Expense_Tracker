# models/__init__.py

# Import the main db instance and base models
from .models import *
from .income_models import *
from .budget_models import *
from .budget_helpers import *  # ADD THIS LINE
from .budget_preferences import *  # ADD THIS LINE

# Make sure all models are available when importing from models
__all__ = [
    'db', 'User', 'Group', 'Category', 'Expense', 'ExpenseParticipant',
    'Balance', 'Settlement', 'RecurringPayment', 'user_groups',
    'IncomeCategory', 'IncomeEntry', 'IncomeAllocationCategory', 'IncomeAllocation',
    'BudgetCategory', 'BudgetSnapshot', 'BudgetPreference',
    # Helper functions
    'get_budget_type_for_expense', 
    'get_budget_type_for_allocation',
    'auto_classify_category_name',
    'get_default_allocation_rules',
    'get_category_specific_rules',
    'create_default_budget_mappings',
    'calculate_trend',
    'predict_next_month',
    'calculate_variance',
    'detect_anomalies',
    'generate_spending_recommendations',
    'calculate_50_30_20_allocation',
]