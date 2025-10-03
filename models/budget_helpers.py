# models/budget_helpers.py - Helper functions for budget analytics

"""
Budget helper functions for classification, analysis, and data operations.
Separated from models for better organization and testability.
"""

from models import db
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json


# ============================================================================
# Budget Type Classification Helpers
# ============================================================================

def get_budget_type_for_expense(expense):
    """
    Get the budget type for an expense based on its category.
    
    Args:
        expense: Expense model instance
        
    Returns:
        str: 'essential', 'investment', 'emergency', 'personal', or 'debt'
    """
    from models.budget_models import BudgetCategory
    
    if not expense.category_obj:
        return 'personal'
    
    budget_cat = BudgetCategory.query.filter_by(
        expense_category_id=expense.category_id,
        group_id=expense.group_id
    ).first()
    
    if budget_cat:
        return budget_cat.budget_type
    
    # Auto-classify if no mapping exists
    return auto_classify_category_name(expense.category_obj.name)


def get_budget_type_for_allocation(allocation):
    """
    Get the budget type for an income allocation.
    
    Args:
        allocation: IncomeAllocation model instance
        
    Returns:
        str: 'essential', 'investment', 'emergency', 'personal', or 'debt'
    """
    from models.budget_models import BudgetCategory
    
    if not allocation.allocation_category_obj:
        return 'personal'
    
    budget_cat = BudgetCategory.query.filter_by(
        allocation_category_id=allocation.allocation_category_id
    ).first()
    
    if budget_cat:
        return budget_cat.budget_type
    
    # Auto-classify if no mapping exists
    return auto_classify_category_name(allocation.allocation_category_obj.name)


def auto_classify_category_name(category_name):
    """
    Automatically classify a category into a budget type based on name.
    Uses pattern matching for intelligent categorization.
    
    Args:
        category_name: str - Name of the category
        
    Returns:
        str: Budget type ('essential', 'investment', 'emergency', 'personal', 'debt')
    """
    name_lower = category_name.lower()
    
    # Essential categories - basic living expenses
    essential_keywords = [
        'rent', 'mortgage', 'utilities', 'utility', 'groceries', 
        'grocery', 'insurance', 'phone', 'internet', 'gas', 
        'electric', 'water', 'healthcare', 'health', 'medical',
        'transportation', 'transit', 'commute', 'childcare'
    ]
    
    # Investment categories - wealth building
    investment_keywords = [
        '401', 'ira', 'roth', 'invest', 'stock', 'mutual', 
        'retirement', 'pension', 'portfolio', 'brokerage',
        'index fund', 'etf', 'bond'
    ]
    
    # Emergency fund categories - safety net
    emergency_keywords = [
        'emergency', 'savings', 'save', 'rainy day', 'buffer'
    ]
    
    # Debt categories - debt repayment
    debt_keywords = [
        'debt', 'loan', 'credit card', 'payment', 'student loan',
        'car loan', 'personal loan', 'line of credit', 'mortgage payment'
    ]
    
    # Check each type (order matters - most specific first)
    if any(keyword in name_lower for keyword in investment_keywords):
        return 'investment'
    elif any(keyword in name_lower for keyword in emergency_keywords):
        return 'emergency'
    elif any(keyword in name_lower for keyword in debt_keywords):
        return 'debt'
    elif any(keyword in name_lower for keyword in essential_keywords):
        return 'essential'
    else:
        return 'personal'

def classify_allocation_into_bucket(allocation_category_name):
    """
    Classify an income allocation category into one of three buckets:
    'investments', 'savings', or 'spending'
    
    Args:
        allocation_category_name: str - Name of the allocation category
        
    Returns:
        str: 'investments', 'savings', or 'spending'
    """
    name_lower = allocation_category_name.lower()
    
    # Investment keywords
    investment_keywords = [
        '401', 'ira', 'roth', 'invest', 'stock', 'mutual', 
        'retirement', 'pension', 'portfolio', 'brokerage',
        'index fund', 'etf', 'bond', 'crypto', 'bitcoin'
    ]
    
    # Savings keywords
    savings_keywords = [
        'savings', 'save', 'emergency', 'rainy day', 'buffer',
        'reserve', 'nest egg'
    ]
    
    # Spending keywords (checking, cash, etc.)
    spending_keywords = [
        'checking', 'cash', 'wallet', 'debit', 'spending',
        'bills', 'expenses'
    ]
    
    # Check each type (order matters - most specific first)
    if any(keyword in name_lower for keyword in investment_keywords):
        return 'investments'
    elif any(keyword in name_lower for keyword in savings_keywords):
        return 'savings'
    elif any(keyword in name_lower for keyword in spending_keywords):
        return 'spending'
    else:
        # Default to spending (including "Other")
        return 'spending'


def group_similar_strings(strings, similarity_threshold=0.7):
    """
    Group similar strings together using simple keyword matching.
    
    Args:
        strings: list - List of strings to group
        similarity_threshold: float - Not used, kept for future enhancement
        
    Returns:
        dict: Mapping of representative string to list of similar strings
    """
    if not strings:
        return {}
    
    # Simple grouping by common keywords
    groups = {}
    
    for s in strings:
        s_lower = s.lower().strip()
        
        # Find if this belongs to an existing group
        found_group = False
        for group_key in groups.keys():
            group_key_lower = group_key.lower()
            
            # Check if they share common words (simple approach)
            s_words = set(s_lower.split())
            key_words = set(group_key_lower.split())
            
            # If they share at least one significant word (length > 3)
            common_words = [w for w in s_words & key_words if len(w) > 3]
            
            if common_words:
                groups[group_key].append(s)
                found_group = True
                break
        
        # If no group found, create new group
        if not found_group:
            groups[s] = [s]
    
    return groups

# ============================================================================
# Default Rules and Mappings
# ============================================================================

def get_default_allocation_rules(budget_type):
    """
    Get default allocation rules based on budget type.
    Based on common financial planning wisdom (50/30/20 rule and variations).
    
    Args:
        budget_type: str - Type of budget category
        
    Returns:
        dict: Allocation rules with min/max/recommended percentages
    """
    defaults = {
        'essential': {
            'min_percent': 50,
            'max_percent': 70,
            'recommended_percent': 50,
            'description': 'Essential living expenses (rent, utilities, groceries, etc.)'
        },
        'investment': {
            'min_percent': 10,
            'max_percent': 30,
            'recommended_percent': 20,
            'description': 'Long-term investments and retirement savings'
        },
        'emergency': {
            'min_percent': 5,
            'max_percent': 15,
            'recommended_percent': 10,
            'description': 'Emergency fund and rainy day savings'
        },
        'personal': {
            'min_percent': 10,
            'max_percent': 30,
            'recommended_percent': 15,
            'description': 'Discretionary spending (entertainment, hobbies, etc.)'
        },
        'debt': {
            'min_percent': 0,
            'max_percent': 20,
            'recommended_percent': 5,
            'description': 'Debt repayment (beyond minimum payments)'
        }
    }
    
    return defaults.get(budget_type, {
        'min_percent': 0,
        'max_percent': 100,
        'recommended_percent': 10,
        'description': 'General allocation'
    })


def get_category_specific_rules(category_name):
    """
    Get specific allocation rules for well-known categories.
    Provides more granular recommendations than budget type alone.
    
    Args:
        category_name: str - Name of the category
        
    Returns:
        dict: Allocation rules specific to this category
    """
    name_lower = category_name.lower()
    
    specific_rules = {
        'rent': {'min_percent': 25, 'max_percent': 35, 'recommended_percent': 30},
        'mortgage': {'min_percent': 25, 'max_percent': 35, 'recommended_percent': 30},
        'groceries': {'min_percent': 10, 'max_percent': 20, 'recommended_percent': 15},
        'transportation': {'min_percent': 5, 'max_percent': 15, 'recommended_percent': 10},
        'utilities': {'min_percent': 5, 'max_percent': 10, 'recommended_percent': 7},
        'insurance': {'min_percent': 5, 'max_percent': 12, 'recommended_percent': 8},
        '401(k)': {'min_percent': 10, 'max_percent': 20, 'recommended_percent': 15},
        'roth ira': {'min_percent': 5, 'max_percent': 15, 'recommended_percent': 10},
        'emergency fund': {'min_percent': 5, 'max_percent': 15, 'recommended_percent': 10},
        'entertainment': {'min_percent': 5, 'max_percent': 15, 'recommended_percent': 8},
        'dining out': {'min_percent': 3, 'max_percent': 10, 'recommended_percent': 5},
    }
    
    # Check for exact or partial matches
    for key, rules in specific_rules.items():
        if key in name_lower:
            return rules
    
    # Fallback to budget type defaults
    budget_type = auto_classify_category_name(category_name)
    return get_default_allocation_rules(budget_type)


def create_default_budget_mappings(group_id):
    """
    Create default budget category mappings for a group.
    Called when a new personal tracker is created or when initializing budgets.
    
    Args:
        group_id: int - ID of the group
        
    Returns:
        list: Created BudgetCategory instances
    """
    from models import Category
    from models.income_models import IncomeAllocationCategory
    from models.budget_models import BudgetCategory
    
    created_mappings = []
    
    # Map expense categories
    expense_categories = Category.query.filter_by(group_id=group_id).all()
    for category in expense_categories:
        # Check if mapping already exists
        existing = BudgetCategory.query.filter_by(
            expense_category_id=category.id,
            group_id=group_id
        ).first()
        
        if not existing:
            budget_type = auto_classify_category_name(category.name)
            rules = get_category_specific_rules(category.name)
            
            mapping = BudgetCategory(
                expense_category_id=category.id,
                group_id=group_id,
                budget_type=budget_type,
                allocation_rules=json.dumps(rules)
            )
            db.session.add(mapping)
            created_mappings.append(mapping)
    
    # Map allocation categories
    allocation_categories = IncomeAllocationCategory.query.filter_by(group_id=group_id).all()
    for category in allocation_categories:
        # Check if mapping already exists
        existing = BudgetCategory.query.filter_by(
            allocation_category_id=category.id,
            group_id=group_id
        ).first()
        
        if not existing:
            budget_type = auto_classify_category_name(category.name)
            rules = get_category_specific_rules(category.name)
            
            mapping = BudgetCategory(
                allocation_category_id=category.id,
                group_id=group_id,
                budget_type=budget_type,
                allocation_rules=json.dumps(rules)
            )
            db.session.add(mapping)
            created_mappings.append(mapping)
    
    if created_mappings:
        db.session.commit()
    
    return created_mappings


# ============================================================================
# Trend Analysis Helpers
# ============================================================================

def calculate_trend(snapshots, metric='total_expenses'):
    """
    Calculate trend direction for a metric across snapshots.
    
    Args:
        snapshots: list - List of BudgetSnapshot instances
        metric: str - Metric to analyze (e.g., 'total_expenses', 'total_income')
        
    Returns:
        str: 'increasing', 'decreasing', or 'stable'
    """
    if len(snapshots) < 2:
        return 'stable'
    
    # Sort by date (oldest first)
    sorted_snapshots = sorted(snapshots, key=lambda s: s.snapshot_date)
    
    # Get values
    values = [getattr(s, metric, 0) for s in sorted_snapshots]
    
    # Simple linear trend using first half vs second half
    first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
    second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
    
    # Calculate percentage change
    if first_half_avg > 0:
        change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        if change_percent > 5:
            return 'increasing'
        elif change_percent < -5:
            return 'decreasing'
    
    return 'stable'


def predict_next_month(snapshots, metric='total_expenses'):
    """
    Simple prediction for next month based on historical data.
    Uses moving average for prediction.
    
    Args:
        snapshots: list - List of BudgetSnapshot instances
        metric: str - Metric to predict
        
    Returns:
        float: Predicted value for next month
    """
    if not snapshots:
        return 0
    
    # Sort by date (newest first)
    sorted_snapshots = sorted(snapshots, key=lambda s: s.snapshot_date, reverse=True)
    
    # Take last 3 months for moving average
    recent = sorted_snapshots[:3]
    values = [getattr(s, metric, 0) for s in recent]
    
    if values:
        return sum(values) / len(values)
    
    return 0


def calculate_variance(snapshots, metric='total_expenses'):
    """
    Calculate variance (standard deviation) for a metric across snapshots.
    Higher variance indicates less predictable spending.
    
    Args:
        snapshots: list - List of BudgetSnapshot instances
        metric: str - Metric to analyze
        
    Returns:
        tuple: (mean, std_dev, coefficient_of_variation)
    """
    if not snapshots:
        return (0, 0, 0)
    
    values = [getattr(s, metric, 0) for s in snapshots]
    
    # Calculate mean
    mean = sum(values) / len(values)
    
    # Calculate standard deviation
    if len(values) > 1:
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        std_dev = variance ** 0.5
        
        # Coefficient of variation (normalized measure)
        cv = (std_dev / mean * 100) if mean > 0 else 0
        
        return (mean, std_dev, cv)
    
    return (mean, 0, 0)


def detect_anomalies(snapshots, metric='total_expenses', threshold=2.0):
    """
    Detect anomalous spending patterns using standard deviation.
    
    Args:
        snapshots: list - List of BudgetSnapshot instances
        metric: str - Metric to analyze
        threshold: float - Number of standard deviations for anomaly detection
        
    Returns:
        list: List of tuples (snapshot, z_score) for anomalies
    """
    if len(snapshots) < 3:
        return []
    
    values = [getattr(s, metric, 0) for s in snapshots]
    mean = sum(values) / len(values)
    
    # Calculate standard deviation
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return []
    
    # Find anomalies
    anomalies = []
    for snapshot, value in zip(snapshots, values):
        z_score = (value - mean) / std_dev
        if abs(z_score) > threshold:
            anomalies.append((snapshot, z_score))
    
    return anomalies


# ============================================================================
# Recommendation Helpers
# ============================================================================

def generate_spending_recommendations(snapshot, previous_snapshot=None):
    """
    Generate personalized spending recommendations based on snapshot data.
    
    Args:
        snapshot: BudgetSnapshot - Current month's snapshot
        previous_snapshot: BudgetSnapshot - Previous month's snapshot (optional)
        
    Returns:
        list: List of recommendation strings
    """
    recommendations = []
    
    # Check savings rate
    if snapshot.savings_rate < 10:
        recommendations.append(
            f"Your savings rate is {snapshot.savings_rate:.1f}%. "
            f"Try to save at least 10-20% of your income."
        )
    elif snapshot.savings_rate > 30:
        recommendations.append(
            f"Great job! You're saving {snapshot.savings_rate:.1f}% of your income."
        )
    
    # Check essential spending ratio
    essential_ratio = snapshot.get_essential_ratio()
    if essential_ratio > 70:
        recommendations.append(
            f"Essential expenses are {essential_ratio:.1f}% of your budget. "
            f"Consider ways to reduce fixed costs."
        )
    
    # Compare to previous month (with zero-division protection)
    if previous_snapshot and previous_snapshot.total_expenses > 0:
        expense_change = ((snapshot.total_expenses - previous_snapshot.total_expenses) 
                         / previous_snapshot.total_expenses * 100)
        
        if expense_change > 15:
            recommendations.append(
                f"Your spending increased by {expense_change:.1f}% compared to last month. "
                f"Review your discretionary expenses."
            )
        elif expense_change < -15:
            recommendations.append(
                f"Great! You reduced spending by {abs(expense_change):.1f}% this month."
            )
    elif previous_snapshot and previous_snapshot.total_expenses == 0 and snapshot.total_expenses > 0:
        recommendations.append(
            f"You started tracking expenses this month. Keep it up!"
        )
    
    # Check for overspending
    discretionary = snapshot.get_discretionary_spending()
    if snapshot.total_income > 0:
        discretionary_percent = (discretionary / snapshot.total_income) * 100
        if discretionary_percent > 35:
            recommendations.append(
                f"Discretionary spending is {discretionary_percent:.1f}% of income. "
                f"Consider the 50/30/20 rule: 50% essentials, 30% wants, 20% savings."
            )
    
    return recommendations if recommendations else ["You're on track! Keep up the good work."]


def calculate_50_30_20_allocation(monthly_income):
    """
    Calculate 50/30/20 budget allocation.
    50% needs, 30% wants, 20% savings/debt
    
    Args:
        monthly_income: float - Monthly income amount
        
    Returns:
        dict: Allocation breakdown
    """
    return {
        'essentials': monthly_income * 0.50,
        'personal': monthly_income * 0.30,
        'savings_and_debt': monthly_income * 0.20,
        'breakdown': {
            'essentials_percent': 50,
            'personal_percent': 30,
            'savings_percent': 15,
            'debt_percent': 5
        }
    }


# ============================================================================
# Utility Functions
# ============================================================================

def get_first_day_of_month(year, month):
    """Get first day of month as date object"""
    return date(year, month, 1)


def get_last_day_of_month(year, month):
    """Get last day of month as date object"""
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - relativedelta(days=1)


def get_month_range(year, month):
    """Get (first_day, last_day) tuple for a month"""
    return (get_first_day_of_month(year, month), 
            get_last_day_of_month(year, month))


def format_currency(amount):
    """Format amount as currency string"""
    return f"${amount:,.2f}"


def format_percentage(value):
    """Format value as percentage string"""
    return f"{value:.1f}%"