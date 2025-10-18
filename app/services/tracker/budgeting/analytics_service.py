# app/services/tracker/budgeting/analytics_service.py - Budget analytics data aggregation

"""
Budget Analytics Service - Core data science and analytics engine.

This service handles:
- Data aggregation from expenses and income
- Time-series analysis
- Trend detection
- Statistical calculations
- Snapshot generation for historical tracking
"""

from models import db, Expense, ExpenseParticipant, Group
from models.income_models import IncomeEntry, IncomeAllocation
from models.budget_models import BudgetCategory, BudgetSnapshot
from models.budget_helpers import (
    get_budget_type_for_expense,
    get_budget_type_for_allocation,
    calculate_trend,
    predict_next_month,
    calculate_variance,
    detect_anomalies,
    generate_spending_recommendations,
    get_month_range
)
from sqlalchemy import func, and_, extract
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class BudgetAnalyticsService:
    """
    Main service for budget analytics operations.
    Provides data science capabilities for financial tracking.
    """
    
    @staticmethod
    def get_monthly_summary(group_id, user_id, year, month):
        """
        Get comprehensive monthly summary for a user.
        
        This is the main method for the analytics dashboard - it aggregates
        all financial data for a specific month.
        
        Args:
            group_id: int - Group ID
            user_id: int - User ID
            year: int - Year
            month: int - Month (1-12)
            
        Returns:
            dict: Complete monthly summary with all metrics
        """
        try:
            # Get date range for the month
            start_date, end_date = get_month_range(year, month)
            
            # Calculate all metrics
            # Check if this is a personal tracker
            group = Group.query.get(group_id)
            is_personal_tracker = group.is_personal_tracker if group else False

            # Calculate expense metrics (always available)
            expense_data = BudgetAnalyticsService._calculate_expense_metrics(
                group_id, user_id, start_date, end_date
            )

            # Calculate income metrics (only for personal trackers)
            if is_personal_tracker:
                income_data = BudgetAnalyticsService._calculate_income_metrics(
                    group_id, user_id, start_date, end_date
                )
                
                allocation_data = BudgetAnalyticsService._calculate_allocation_metrics(
                    group_id, user_id, start_date, end_date
                )
            else:
                # Return empty income/allocation data for group trackers
                income_data = {
                    'total': 0,
                    'count': 0,
                    'by_category': {},
                    'entries': []
                }
                
                allocation_data = {
                    'total_allocated': 0,
                    'by_category': {},
                    'by_budget_type': {},
                    'by_bucket': {'investments': 0, 'savings': 0, 'spending': 0},
                    'allocation_details': {},
                    'bucket_details': {'investments': {}, 'savings': {}, 'spending': {}}
                }
            
            # Combine everything
            summary = {
                'period': {
                    'year': year,
                    'month': month,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'income': income_data,
                'expenses': expense_data,
                'allocations': allocation_data,
                'net_summary': BudgetAnalyticsService._calculate_net_summary(
                    income_data, expense_data
                )
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating monthly summary: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _calculate_income_metrics(group_id, user_id, start_date, end_date):
        """Calculate income metrics for a period"""
        # Get all income entries for the period
        income_entries = IncomeEntry.query.filter(
            and_(
                IncomeEntry.group_id == group_id,
                IncomeEntry.user_id == user_id,
                IncomeEntry.date >= start_date,
                IncomeEntry.date <= end_date
            )
        ).all()
        
        total_income = sum(entry.amount for entry in income_entries)
        
        # Calculate income by category
        income_by_category = defaultdict(float)
        for entry in income_entries:
            category_name = entry.income_category_obj.name if entry.income_category_obj else 'Unknown'
            income_by_category[category_name] += entry.amount
        
        return {
            'total': total_income,
            'count': len(income_entries),
            'by_category': dict(income_by_category),
            'entries': [
                {
                    'id': entry.id,
                    'amount': entry.amount,
                    'category': entry.income_category_obj.name if entry.income_category_obj else 'Unknown',
                    'description': entry.description,
                    'date': entry.date.isoformat()
                }
                for entry in income_entries
            ]
        }
    
    @staticmethod
    def _calculate_expense_metrics(group_id, user_id, start_date, end_date):
        """Calculate expense metrics for a period"""
        from models import Group
        
        # Check if this is a personal tracker or group tracker
        group = Group.query.get(group_id)
        is_personal_tracker = group.is_personal_tracker if group else False
        
        if is_personal_tracker:
            # Personal tracker: Only expenses where user participated
            expenses = db.session.query(Expense).join(ExpenseParticipant).filter(
                and_(
                    Expense.group_id == group_id,
                    ExpenseParticipant.user_id == user_id,
                    Expense.date >= start_date,
                    Expense.date <= end_date
                )
            ).all()
        else:
            # Group tracker: ALL expenses in the group
            expenses = Expense.query.filter(
                and_(
                    Expense.group_id == group_id,
                    Expense.date >= start_date,
                    Expense.date <= end_date
                )
            ).all()
        
        # Calculate totals and breakdowns
        total_expenses = 0
        total_essentials = 0
        total_discretionary = 0
        
        expenses_by_category = defaultdict(float)
        expenses_by_budget_type = defaultdict(float)
        category_details = defaultdict(lambda: {'total': 0, 'items': []})
        
        for expense in expenses:
            if is_personal_tracker:
                # Personal tracker: Get user's share of this expense
                participant = ExpenseParticipant.query.filter_by(
                    expense_id=expense.id,
                    user_id=user_id
                ).first()
                
                if not participant:
                    continue
                
                user_share = participant.amount_owed
            else:
                # Group tracker: Use the full expense amount
                user_share = expense.amount
            total_expenses += user_share
            
            # Classify expense
            budget_type = get_budget_type_for_expense(expense)
            expenses_by_budget_type[budget_type] += user_share
            
            if budget_type == 'essential':
                total_essentials += user_share
            else:
                total_discretionary += user_share
            
            # Category breakdown
            category_name = expense.category_obj.name if expense.category_obj else 'Unknown'
            expenses_by_category[category_name] += user_share
            
            # Store detailed items
            category_details[category_name]['total'] += user_share
            category_details[category_name]['items'].append({
                'id': expense.id,
                'amount': user_share,
                'description': expense.category_description or 'No description',
                'date': expense.date.isoformat(),
                'budget_type': budget_type
            })
        
        return {
            'total': total_expenses,
            'essentials': total_essentials,
            'discretionary': total_discretionary,
            'count': len(expenses),
            'by_category': dict(expenses_by_category),
            'by_budget_type': dict(expenses_by_budget_type),
            'category_details': dict(category_details)
        }
    
    @staticmethod
    def _calculate_allocation_metrics(group_id, user_id, start_date, end_date):
        """Calculate income allocation metrics for a period - with bucket classification"""
        from models.budget_helpers import classify_allocation_into_bucket
        
        # Get all income entries for the period
        income_entries = IncomeEntry.query.filter(
            and_(
                IncomeEntry.group_id == group_id,
                IncomeEntry.user_id == user_id,
                IncomeEntry.date >= start_date,
                IncomeEntry.date <= end_date
            )
        ).all()
        
        # Get all allocations for these income entries
        income_entry_ids = [entry.id for entry in income_entries]
        
        if not income_entry_ids:
            return {
                'total_allocated': 0,
                'by_category': {},
                'by_budget_type': {},
                'by_bucket': {'investments': 0, 'savings': 0, 'spending': 0},
                'allocation_details': {},
                'bucket_details': {
                    'investments': {},
                    'savings': {},
                    'spending': {}
                }
            }
        
        allocations = IncomeAllocation.query.filter(
            IncomeAllocation.income_entry_id.in_(income_entry_ids)
        ).all()
        
        total_allocated = sum(alloc.amount for alloc in allocations)
        
        # Calculate allocations by category, budget type, and bucket
        allocations_by_category = defaultdict(float)
        allocations_by_budget_type = defaultdict(float)
        allocations_by_bucket = defaultdict(float)
        allocation_details = defaultdict(lambda: {'total': 0, 'items': []})
        bucket_details = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'items': []}))
        
        for allocation in allocations:
            budget_type = get_budget_type_for_allocation(allocation)
            category_name = allocation.allocation_category_obj.name if allocation.allocation_category_obj else 'Unknown'
            
            # NEW: Classify into bucket
            bucket = classify_allocation_into_bucket(category_name)
            
            allocations_by_category[category_name] += allocation.amount
            allocations_by_budget_type[budget_type] += allocation.amount
            allocations_by_bucket[bucket] += allocation.amount
            
            # Store details
            allocation_item = {
                'id': allocation.id,
                'amount': allocation.amount,
                'notes': allocation.notes or category_name,  # Default to category name if no notes
                'budget_type': budget_type,
                'bucket': bucket,
                'income_entry_date': allocation.income_entry.date.isoformat() if allocation.income_entry else None
            }
            
            allocation_details[category_name]['total'] += allocation.amount
            allocation_details[category_name]['items'].append(allocation_item)
            
            # Store in bucket details
            bucket_details[bucket][category_name]['total'] += allocation.amount
            bucket_details[bucket][category_name]['items'].append(allocation_item)
        
        return {
            'total_allocated': total_allocated,
            'by_category': dict(allocations_by_category),
            'by_budget_type': dict(allocations_by_budget_type),
            'by_bucket': dict(allocations_by_bucket),
            'allocation_details': dict(allocation_details),
            'bucket_details': {
                bucket: dict(categories) 
                for bucket, categories in bucket_details.items()
            }
        }
    
    @staticmethod
    def _calculate_net_summary(income_data, expense_data):
        """Calculate net financial summary"""
        total_income = income_data.get('total', 0)
        total_expenses = expense_data.get('total', 0)
        net_cashflow = total_income - total_expenses
        
        savings_rate = 0
        if total_income > 0:
            savings_rate = (net_cashflow / total_income) * 100
        
        essential_ratio = 0
        if total_expenses > 0:
            essential_ratio = (expense_data.get('essentials', 0) / total_expenses) * 100
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_cashflow': net_cashflow,
            'savings_rate': savings_rate,
            'essential_ratio': essential_ratio,
            'discretionary_left': total_income - expense_data.get('essentials', 0) if total_income > 0 else 0
        }
    
    @staticmethod
    def get_spending_trends(group_id, user_id, months=6):
        """
        Get spending trends over the last N months.
        
        Args:
            group_id: int - Group ID
            user_id: int - User ID
            months: int - Number of months to analyze
            
        Returns:
            dict: Trend analysis with time-series data
        """
        try:
            # Get snapshots for analysis
            snapshots = BudgetSnapshot.get_last_n_months(group_id, user_id, months)
            
            if not snapshots:
                return BudgetAnalyticsService._generate_empty_trend_data(months)
            
            # Sort by date (oldest first for time series)
            snapshots.sort(key=lambda s: s.snapshot_date)
            
            # Build time series data
            time_series = []
            for snapshot in snapshots:
                time_series.append({
                    'month': snapshot.snapshot_date.strftime('%b %Y'),
                    'date': snapshot.snapshot_date.isoformat(),
                    'income': snapshot.total_income,
                    'expenses': snapshot.total_expenses,
                    'essentials': snapshot.total_essentials,
                    'discretionary': snapshot.get_discretionary_spending(),
                    'savings_rate': snapshot.savings_rate,
                    'net_cashflow': snapshot.total_income - snapshot.total_expenses
                })
            
            # Calculate trends
            expense_trend = calculate_trend(snapshots, 'total_expenses')
            income_trend = calculate_trend(snapshots, 'total_income')
            
            # Calculate statistics
            expense_stats = calculate_variance(snapshots, 'total_expenses')
            income_stats = calculate_variance(snapshots, 'total_income')
            
            # Predictions
            predicted_expenses = predict_next_month(snapshots, 'total_expenses')
            predicted_income = predict_next_month(snapshots, 'total_income')
            
            # Anomaly detection
            expense_anomalies = detect_anomalies(snapshots, 'total_expenses', threshold=2.0)
            
            return {
                'time_series': time_series,
                'trends': {
                    'expenses': expense_trend,
                    'income': income_trend
                },
                'statistics': {
                    'expenses': {
                        'mean': expense_stats[0],
                        'std_dev': expense_stats[1],
                        'coefficient_of_variation': expense_stats[2]
                    },
                    'income': {
                        'mean': income_stats[0],
                        'std_dev': income_stats[1],
                        'coefficient_of_variation': income_stats[2]
                    }
                },
                'predictions': {
                    'next_month_expenses': predicted_expenses,
                    'next_month_income': predicted_income,
                    'next_month_savings': predicted_income - predicted_expenses
                },
                'anomalies': [
                    {
                        'date': anomaly[0].snapshot_date.isoformat(),
                        'month': anomaly[0].snapshot_date.strftime('%b %Y'),
                        'z_score': anomaly[1],
                        'amount': anomaly[0].total_expenses
                    }
                    for anomaly in expense_anomalies
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating spending trends: {e}")
            import traceback
            traceback.print_exc()
            return BudgetAnalyticsService._generate_empty_trend_data(months)
    
    @staticmethod
    def _generate_empty_trend_data(months):
        """Generate empty trend data structure"""
        today = date.today()
        time_series = []
        
        for i in range(months):
            month_date = today - relativedelta(months=months - i - 1)
            time_series.append({
                'month': month_date.strftime('%b %Y'),
                'date': month_date.replace(day=1).isoformat(),
                'income': 0,
                'expenses': 0,
                'essentials': 0,
                'discretionary': 0,
                'savings_rate': 0,
                'net_cashflow': 0
            })
        
        return {
            'time_series': time_series,
            'trends': {'expenses': 'stable', 'income': 'stable'},
            'statistics': {
                'expenses': {'mean': 0, 'std_dev': 0, 'coefficient_of_variation': 0},
                'income': {'mean': 0, 'std_dev': 0, 'coefficient_of_variation': 0}
            },
            'predictions': {
                'next_month_expenses': 0,
                'next_month_income': 0,
                'next_month_savings': 0
            },
            'anomalies': []
        }
    
    @staticmethod
    def generate_snapshot(group_id, user_id, year, month):
        """
        Generate and save a budget snapshot for a specific month.
        This creates historical data for trend analysis.
        
        Args:
            group_id: int - Group ID
            user_id: int - User ID
            year: int - Year
            month: int - Month (1-12)
            
        Returns:
            BudgetSnapshot: Generated snapshot instance
        """
        try:
            # Get or create snapshot
            snapshot = BudgetSnapshot.get_or_create_for_month(group_id, user_id, year, month)
            
            # Get monthly summary
            summary = BudgetAnalyticsService.get_monthly_summary(group_id, user_id, year, month)
            
            if not summary:
                logger.error(f"Failed to generate summary for snapshot")
                return None
            
            # Update snapshot with calculated data
            snapshot.total_income = summary['income']['total']
            snapshot.total_expenses = summary['expenses']['total']
            snapshot.total_essentials = summary['expenses']['essentials']
            snapshot.total_discretionary = summary['expenses']['discretionary']
            
            # Store breakdowns
            snapshot.set_allocation_breakdown(summary['allocations']['by_budget_type'])
            snapshot.set_category_breakdown(summary['expenses']['by_category'])
            
            # Calculate and store metrics
            snapshot.calculate_savings_rate()
            
            # Calculate variance from previous month
            previous_month_date = date(year, month, 1) - relativedelta(months=1)
            previous_snapshot = BudgetSnapshot.query.filter_by(
                group_id=group_id,
                user_id=user_id,
                snapshot_date=previous_month_date
            ).first()
            
            if previous_snapshot and previous_snapshot.total_expenses > 0:
                variance = ((snapshot.total_expenses - previous_snapshot.total_expenses) 
                           / previous_snapshot.total_expenses * 100)
                snapshot.expense_variance = variance
            else:
                snapshot.expense_variance = 0
            
            db.session.commit()
            
            logger.info(f"Generated snapshot for {year}-{month}: ${snapshot.total_income:.2f} income, ${snapshot.total_expenses:.2f} expenses")
            
            return snapshot
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating snapshot: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def generate_snapshots_for_year(group_id, user_id, year):
        """
        Generate snapshots for all months in a year.
        Useful for backfilling historical data.
        
        Args:
            group_id: int - Group ID
            user_id: int - User ID
            year: int - Year
            
        Returns:
            list: List of generated snapshots
        """
        snapshots = []
        current_date = date.today()
        
        for month in range(1, 13):
            # Don't generate snapshots for future months
            if year == current_date.year and month > current_date.month:
                break
            
            snapshot = BudgetAnalyticsService.generate_snapshot(group_id, user_id, year, month)
            if snapshot:
                snapshots.append(snapshot)
        
        return snapshots
    
    @staticmethod
    def get_category_analysis(group_id, user_id, year, month):
        """
        Get detailed category-level analysis with sub-breakdowns.
        
        This provides the data for category dropdowns and pie charts.
        
        Args:
            group_id: int - Group ID
            user_id: int - User ID
            year: int - Year
            month: int - Month (1-12)
            
        Returns:
            dict: Category analysis with sub-category breakdowns
        """
        try:
            start_date, end_date = get_month_range(year, month)
            
            # Get all expenses for the period
            expenses = db.session.query(Expense).join(ExpenseParticipant).filter(
                and_(
                    Expense.group_id == group_id,
                    ExpenseParticipant.user_id == user_id,
                    Expense.date >= start_date,
                    Expense.date <= end_date
                )
            ).all()
            
            # Build category analysis
            category_analysis = defaultdict(lambda: {
                'total': 0,
                'count': 0,
                'budget_type': 'personal',
                'subcategories': defaultdict(lambda: {'total': 0, 'count': 0, 'items': []})
            })
            
            for expense in expenses:
                # Get user's share
                participant = ExpenseParticipant.query.filter_by(
                    expense_id=expense.id,
                    user_id=user_id
                ).first()
                
                if not participant:
                    continue
                
                user_share = participant.amount_owed
                category_name = expense.category_obj.name if expense.category_obj else 'Unknown'
                subcategory = expense.category_description or 'Other'
                budget_type = get_budget_type_for_expense(expense)
                
                # Update category totals
                category_analysis[category_name]['total'] += user_share
                category_analysis[category_name]['count'] += 1
                category_analysis[category_name]['budget_type'] = budget_type
                
                # Update subcategory
                category_analysis[category_name]['subcategories'][subcategory]['total'] += user_share
                category_analysis[category_name]['subcategories'][subcategory]['count'] += 1
                category_analysis[category_name]['subcategories'][subcategory]['items'].append({
                    'id': expense.id,
                    'amount': user_share,
                    'date': expense.date.isoformat(),
                    'payer': expense.user.name if expense.user else 'Unknown'
                })
            
            # Convert to regular dict and format for response
            result = {}
            for category, data in category_analysis.items():
                result[category] = {
                    'total': data['total'],
                    'count': data['count'],
                    'budget_type': data['budget_type'],
                    'subcategories': {
                        sub: {
                            'total': subdata['total'],
                            'count': subdata['count'],
                            'percentage': (subdata['total'] / data['total'] * 100) if data['total'] > 0 else 0,
                            'items': subdata['items']
                        }
                        for sub, subdata in data['subcategories'].items()
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating category analysis: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def get_recommendations(group_id, user_id, year, month):
        """
        Generate personalized spending recommendations.
        
        Args:
            group_id: int - Group ID
            user_id: int - User ID
            year: int - Year
            month: int - Month (1-12)
            
        Returns:
            list: List of recommendation strings
        """
        try:
            # Get current month snapshot
            current_snapshot = BudgetSnapshot.query.filter_by(
                group_id=group_id,
                user_id=user_id,
                snapshot_date=date(year, month, 1)
            ).first()
            
            if not current_snapshot:
                # Generate it if it doesn't exist
                current_snapshot = BudgetAnalyticsService.generate_snapshot(group_id, user_id, year, month)
            
            if not current_snapshot:
                return ["Unable to generate recommendations at this time."]
            
            # Get previous month snapshot
            previous_month_date = date(year, month, 1) - relativedelta(months=1)
            previous_snapshot = BudgetSnapshot.query.filter_by(
                group_id=group_id,
                user_id=user_id,
                snapshot_date=previous_month_date
            ).first()
            
            # Generate recommendations
            recommendations = generate_spending_recommendations(current_snapshot, previous_snapshot)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()
            return ["Unable to generate recommendations at this time."]