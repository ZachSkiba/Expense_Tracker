#!/usr/bin/env python3
"""
Database migration script to add missing columns for recurring payments
Run this script to update your production database schema
"""

import os
import sys
from sqlalchemy import text

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

def migrate_database():
    """Add missing columns for recurring payments feature"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 Checking database schema...")
            
            # Check if recurring_payment table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'recurring_payment'
                );
            """))
            recurring_table_exists = result.scalar()
            
            if not recurring_table_exists:
                print("📝 Creating recurring_payment table...")
                # Create the recurring_payment table
                db.session.execute(text("""
                    CREATE TABLE recurring_payment (
                        id SERIAL PRIMARY KEY,
                        amount FLOAT NOT NULL,
                        category_id INTEGER NOT NULL REFERENCES category(id),
                        category_description VARCHAR(255),
                        user_id INTEGER NOT NULL REFERENCES "user"(id),
                        frequency VARCHAR(20) NOT NULL,
                        interval_value INTEGER NOT NULL DEFAULT 1,
                        start_date DATE NOT NULL,
                        next_due_date DATE NOT NULL,
                        end_date DATE,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        participant_ids TEXT NOT NULL
                    );
                """))
                print("✅ Created recurring_payment table")
            else:
                print("✅ recurring_payment table already exists")
            
            # Check if recurring_payment_id column exists in expense table
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'expense' 
                    AND column_name = 'recurring_payment_id'
                );
            """))
            column_exists = result.scalar()
            
            if not column_exists:
                print("📝 Adding recurring_payment_id column to expense table...")
                # Add the missing column
                db.session.execute(text("""
                    ALTER TABLE expense 
                    ADD COLUMN recurring_payment_id INTEGER 
                    REFERENCES recurring_payment(id);
                """))
                print("✅ Added recurring_payment_id column to expense table")
            else:
                print("✅ recurring_payment_id column already exists")
            
            # Commit the changes
            db.session.commit()
            print("✅ Database migration completed successfully!")
            
            # Verify the changes
            print("🔍 Verifying schema...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'expense' 
                AND column_name = 'recurring_payment_id';
            """))
            column_info = result.fetchone()
            
            if column_info:
                print(f"✅ Verified: recurring_payment_id column exists - {column_info}")
            else:
                print("❌ Error: Column verification failed")
                
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()