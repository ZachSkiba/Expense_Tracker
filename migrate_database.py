# migration_add_group_id_postgres.py - PostgreSQL compatible migration

from models import db
from sqlalchemy import text
import sys

def run_migration():
    """Add group_id column to expense_participant table (PostgreSQL)"""
    
    try:
        # Check if column already exists (PostgreSQL way)
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expense_participant'
        """)).fetchall()
        
        column_names = [row[0] for row in result]
        print(f"Current columns in expense_participant: {column_names}")
        
        if 'group_id' not in column_names:
            print("Adding group_id column to expense_participant table...")
            
            # Add the column (PostgreSQL syntax)
            db.session.execute(text("""
                ALTER TABLE expense_participant 
                ADD COLUMN group_id INTEGER REFERENCES "group"(id)
            """))
            
            # Update existing records with group_id from their expenses
            print("Updating existing expense_participant records...")
            db.session.execute(text("""
                UPDATE expense_participant 
                SET group_id = expense.group_id
                FROM expense 
                WHERE expense.id = expense_participant.expense_id
            """))
            
            db.session.commit()
            print("✅ PostgreSQL migration completed successfully!")
            
        else:
            print("✅ group_id column already exists, no migration needed")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.session.rollback()
        return False
    
    return True

if __name__ == "__main__":
    # You can run this script directly
    from app import create_app
    app = create_app()
    
    with app.app_context():
        if run_migration():
            print("Migration completed successfully!")
        else:
            print("Migration failed!")
            sys.exit(1)