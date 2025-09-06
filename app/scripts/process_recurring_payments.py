#!/usr/bin/env python3
"""
Background script to process due recurring payments
This script should be run periodically (e.g., daily via cron job)
"""
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from services.recurring_service import RecurringPaymentService


def main():
    """Main function to process due recurring payments"""
    print(f"[{datetime.now()}] Starting recurring payments processing...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Process all due recurring payments
            created_expenses = RecurringPaymentService.process_due_payments()
            
            if created_expenses:
                print(f"[{datetime.now()}] Successfully processed {len(created_expenses)} recurring payments:")
                for expense in created_expenses:
                    print(f"  - {expense.category_obj.name}: ${expense.amount} (paid by {expense.user.name})")
            else:
                print(f"[{datetime.now()}] No recurring payments were due for processing")
            
            print(f"[{datetime.now()}] Recurring payments processing completed successfully")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error processing recurring payments: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()