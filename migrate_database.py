# migrate_missing_columns.py - Add missing database columns

from app import create_app
from models import db
from sqlalchemy import text
import sys

def add_missing_columns():
    """Add missing columns that cause database errors"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 ADDING MISSING DATABASE COLUMNS...")
            
            inspector = db.inspect(db.engine)
            
            # Check and add missing columns to settlement table
            settlement_columns = [col['name'] for col in inspector.get_columns('settlement')]
            print(f"📋 Current settlement columns: {settlement_columns}")
            
            if 'group_id' not in settlement_columns:
                print("➕ Adding group_id to settlement table...")
                db.session.execute(text('ALTER TABLE settlement ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to settlement table")
            else:
                print("✅ group_id already exists in settlement table")
            
            # Check and add missing columns to balance table
            balance_columns = [col['name'] for col in inspector.get_columns('balance')]
            print(f"📋 Current balance columns: {balance_columns}")
            
            if 'group_id' not in balance_columns:
                print("➕ Adding group_id to balance table...")
                db.session.execute(text('ALTER TABLE balance ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to balance table")
            else:
                print("✅ group_id already exists in balance table")
            
            # Check and add missing columns to expense table
            expense_columns = [col['name'] for col in inspector.get_columns('expense')]
            print(f"📋 Current expense columns: {expense_columns}")
            
            if 'group_id' not in expense_columns:
                print("➕ Adding group_id to expense table...")
                db.session.execute(text('ALTER TABLE expense ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to expense table")
            else:
                print("✅ group_id already exists in expense table")
            
            # Check and add missing columns to category table
            category_columns = [col['name'] for col in inspector.get_columns('category')]
            print(f"📋 Current category columns: {category_columns}")
            
            if 'user_id' not in category_columns:
                print("➕ Adding user_id to category table...")
                db.session.execute(text('ALTER TABLE category ADD COLUMN user_id INTEGER REFERENCES "user"(id)'))
                db.session.commit()
                print("✅ Added user_id to category table")
            else:
                print("✅ user_id already exists in category table")
            
            if 'group_id' not in category_columns:
                print("➕ Adding group_id to category table...")
                db.session.execute(text('ALTER TABLE category ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to category table")
            else:
                print("✅ group_id already exists in category table")
            
            # Check and add missing columns to recurring_payment table
            recurring_columns = [col['name'] for col in inspector.get_columns('recurring_payment')]
            print(f"📋 Current recurring_payment columns: {recurring_columns}")
            
            if 'group_id' not in recurring_columns:
                print("➕ Adding group_id to recurring_payment table...")
                db.session.execute(text('ALTER TABLE recurring_payment ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to recurring_payment table")
            else:
                print("✅ group_id already exists in recurring_payment table")
            
            # Create new tables if they don't exist
            print("➕ Creating any missing tables...")
            db.create_all()
            print("✅ All tables created/verified")
            
            print("\n🎉 DATABASE MIGRATION COMPLETE!")
            print("You can now safely delete users without column errors.")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()

def verify_columns():
    """Verify all required columns exist"""
    app = create_app()
    
    with app.app_context():
        print("🔍 VERIFYING DATABASE COLUMNS...")
        
        inspector = db.inspect(db.engine)
        
        required_columns = {
            'settlement': ['group_id'],
            'balance': ['group_id'], 
            'expense': ['group_id'],
            'category': ['user_id', 'group_id'],
            'recurring_payment': ['group_id']
        }
        
        all_good = True
        
        for table, columns in required_columns.items():
            existing_columns = [col['name'] for col in inspector.get_columns(table)]
            
            for required_col in columns:
                if required_col in existing_columns:
                    print(f"✅ {table}.{required_col} exists")
                else:
                    print(f"❌ {table}.{required_col} MISSING")
                    all_good = False
        
        if all_good:
            print("\n🎉 VERIFICATION PASSED: All required columns exist")
        else:
            print("\n❌ VERIFICATION FAILED: Missing columns found")

if __name__ == "__main__":
    if '--verify' in sys.argv:
        verify_columns()
    else:
        add_missing_columns()
        verify_columns()