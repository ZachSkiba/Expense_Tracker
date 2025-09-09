"""
Database migration script to add recurring payments functionality
Run this after updating your models.py file
"""
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db


def upgrade_database():
    """Add the recurring_payment table and update expense table"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting database migration...")
            
            # Create the recurring_payment table
            db.engine.execute("""
                CREATE TABLE IF NOT EXISTS recurring_payment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    amount FLOAT NOT NULL,
                    category_id INTEGER NOT NULL,
                    category_description VARCHAR(255),
                    user_id INTEGER NOT NULL,
                    frequency VARCHAR(20) NOT NULL,
                    interval_value INTEGER NOT NULL DEFAULT 1,
                    start_date DATE NOT NULL,
                    next_due_date DATE NOT NULL,
                    end_date DATE,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    participant_ids TEXT NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES category(id),
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            """)
            
            # Add recurring_payment_id column to expense table if it doesn't exist
            try:
                db.engine.execute("""
                    ALTER TABLE expense 
                    ADD COLUMN recurring_payment_id INTEGER 
                    REFERENCES recurring_payment(id)
                """)
                print("Added recurring_payment_id column to expense table")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("recurring_payment_id column already exists in expense table")
                else:
                    raise e
            
            print("Database migration completed successfully!")
            print("\nNext steps:")
            print("1. Update your Flask app to register the recurring payments blueprint")
            print("2. Add the recurring payments CSS and JavaScript files")
            print("3. Set up a cron job to run the background processing script")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            sys.exit(1)


if __name__ == '__main__':
    upgrade_database()