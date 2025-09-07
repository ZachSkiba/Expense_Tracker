#!/usr/bin/env python3
"""
Script to process recurring payments
Run this script daily via cron job
"""
import os
import sys

# Add the app directory to the Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(app_dir, 'app'))

from app import create_app
from app.services.recurring_service import RecurringPaymentService
from datetime import datetime

def main():
    """Main function to process recurring payments"""
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Process due payments
            created_expenses = RecurringPaymentService.process_due_payments()
            
            # Log results
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if created_expenses:
                print(f"[{timestamp}] Successfully processed {len(created_expenses)} recurring payments")
                for expense in created_expenses:
                    print(f"  - Created expense ID {expense.id} for ${expense.amount}")
            else:
                print(f"[{timestamp}] No recurring payments were due for processing")
                
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] ERROR: Failed to process recurring payments: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()