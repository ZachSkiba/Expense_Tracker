# migrate_database.py - Add authentication fields to existing User table

from models import db, User, Category, Group
from app import create_app
from sqlalchemy import text
import sys

def migrate_database():
    """Add authentication fields to existing User table and create new tables"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== DATABASE MIGRATION ===")
            print("Adding authentication fields to User table...")
            
            # Check if we need to add new columns to User table
            inspector = db.inspect(db.engine)
            user_columns = [col['name'] for col in inspector.get_columns('user')]
            
            print(f"Current User table columns: {user_columns}")
            
            # Add new columns if they don't exist
            new_columns = [
                ('email', 'VARCHAR(120)'),
                ('username', 'VARCHAR(80)'), 
                ('password_hash', 'VARCHAR(255)'),
                ('is_active', 'BOOLEAN DEFAULT true'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('last_login', 'TIMESTAMP')
            ]
            
            for col_name, col_type in new_columns:
                if col_name not in user_columns:
                    print(f"Adding column: {col_name}")
                    try:
                        db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type}'))
                        db.session.commit()
                        print(f"✅ Added {col_name}")
                    except Exception as e:
                        print(f"⚠️  Column {col_name} might already exist or error: {e}")
                        db.session.rollback()
                else:
                    print(f"✅ Column {col_name} already exists")
            
            # Add unique constraints if they don't exist
            try:
                print("Adding unique constraints...")
                db.session.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON "user" (email)'))
                db.session.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_user_username ON "user" (username)'))
                db.session.commit()
                print("✅ Unique constraints added")
            except Exception as e:
                print(f"⚠️  Constraints might already exist: {e}")
                db.session.rollback()
            
            # Create new tables (Group, user_groups association, etc.)
            print("Creating new tables...")
            db.create_all()
            print("✅ All tables created/updated")
            
            # Update existing users
            print("Updating existing users...")
            legacy_users = User.query.filter(User.email.is_(None)).all()
            
            for user in legacy_users:
                if not user.is_active:
                    user.is_active = True
                if not user.created_at:
                    user.created_at = db.func.now()
                print(f"Updated legacy user: {user.name}")
            
            db.session.commit()
            print(f"✅ Updated {len(legacy_users)} legacy users")
            
            # Add new columns to other tables if needed
            print("Checking other tables...")
            
            # Add group_id to Balance table if it doesn't exist
            balance_columns = [col['name'] for col in inspector.get_columns('balance')]
            if 'group_id' not in balance_columns:
                print("Adding group_id to Balance table...")
                db.session.execute(text('ALTER TABLE balance ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to Balance table")
            
            # Add user_id and group_id to Category table if they don't exist
            category_columns = [col['name'] for col in inspector.get_columns('category')]
            
            if 'user_id' not in category_columns:
                print("Adding user_id to Category table...")
                db.session.execute(text('ALTER TABLE category ADD COLUMN user_id INTEGER REFERENCES "user"(id)'))
                db.session.commit()
                print("✅ Added user_id to Category table")
            
            if 'group_id' not in category_columns:
                print("Adding group_id to Category table...")
                db.session.execute(text('ALTER TABLE category ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to Category table")
            
            # Add group_id to Expense table if it doesn't exist
            expense_columns = [col['name'] for col in inspector.get_columns('expense')]
            if 'group_id' not in expense_columns:
                print("Adding group_id to Expense table...")
                db.session.execute(text('ALTER TABLE expense ADD COLUMN group_id INTEGER REFERENCES "group"(id)'))
                db.session.commit()
                print("✅ Added group_id to Expense table")
            
            print("\n=== MIGRATION COMPLETED SUCCESSFULLY ===")
            
            # Show updated schema
            print("\n=== UPDATED USER TABLE SCHEMA ===")
            updated_user_columns = [col['name'] for col in inspector.get_columns('user')]
            for col in updated_user_columns:
                print(f"  - {col}")
            
            print(f"\n=== SUMMARY ===")
            user_count = User.query.count()
            category_count = Category.query.count()
            group_count = Group.query.count()
            
            print(f"Users: {user_count}")
            print(f"Categories: {category_count}")
            print(f"Groups: {group_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

def verify_migration():
    """Verify the migration was successful"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== VERIFYING MIGRATION ===")
            
            # Test User model functionality
            test_user = User.query.first()
            if test_user:
                print(f"✅ Can query users: {test_user.name}")
                print(f"   Email: {test_user.email or 'Not set'}")
                print(f"   Username: {test_user.username or 'Not set'}")
                print(f"   Active: {test_user.is_active}")
                print(f"   Legacy user: {test_user.is_legacy_user()}")
            
            # Test new methods
            balance = test_user.get_net_balance() if test_user else 0
            print(f"✅ User methods work, balance: ${balance}")
            
            # Test database operations
            result = db.session.execute(text("SELECT 1")).fetchone()
            print(f"✅ Database connection: {'OK' if result else 'FAILED'}")
            
            print("=== VERIFICATION PASSED ===")
            return True
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False

if __name__ == "__main__":
    if '--verify' in sys.argv:
        verify_migration()
    else:
        success = migrate_database()
        if success:
            print("\n🎉 Migration completed! You can now:")
            print("1. Test login/signup functionality")
            print("2. Run: python migrate_database.py --verify")
            print("3. Start your app: python run.py")
        else:
            print("\n💥 Migration failed. Check the errors above.")