# migrate_to_multiuser.py - Script to migrate existing data to multi-user system

"""
Database migration script to convert single-user expense tracker to multi-user system.
This script should be run ONCE after updating your models.

It will:
1. Create the new tables (users, groups, etc.)
2. Create default users from existing User table
3. Create a default "Roommates" group
4. Migrate existing expenses to the group
5. Update categories to be group-specific
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User, Group, Category, Expense, RecurringPayment
from app import create_app

def migrate_database():
    """Run the complete migration process"""
    
    print("🚀 Starting migration to multi-user system...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Step 1: Create all new tables
            print("\n📋 Step 1: Creating new database tables...")
            db.create_all()
            print("✅ Database tables created/updated")
            
            # Step 2: Check if migration is needed
            print("\n🔍 Step 2: Checking if migration is needed...")
            
            # Check if we have any users with passwords (new system)
            users_with_auth = User.query.filter(User.password_hash.isnot(None)).count()
            if users_with_auth > 0:
                print("ℹ️  Migration appears to already be completed (found users with passwords)")
                print("   If you want to re-run migration, please reset your database first.")
                return
            
            # Check if we have existing users (old system)
            existing_users = User.query.all()
            existing_expenses = Expense.query.all()
            existing_categories = Category.query.all()
            
            print(f"   Found {len(existing_users)} existing users")
            print(f"   Found {len(existing_expenses)} existing expenses")  
            print(f"   Found {len(existing_categories)} existing categories")
            
            if not existing_users:
                print("ℹ️  No existing data found. Migration not needed.")
                print("   You can start fresh with the new multi-user system!")
                return
            
            # Step 3: Create default authenticated users
            print("\n👥 Step 3: Converting existing users to authenticated users...")
            
            default_password = "welcome123"  # Users will need to change this
            converted_users = []
            
            for old_user in existing_users:
                # Check if user already has authentication data
                if old_user.password_hash:
                    print(f"   ⏭️  Skipping {old_user.name} (already has password)")
                    converted_users.append(old_user)
                    continue
                
                # Update existing user with authentication fields
                if not hasattr(old_user, 'email') or not old_user.email:
                    # Generate email if not exists
                    old_user.email = f"{old_user.name.lower().replace(' ', '.')}@example.com"
                
                if not hasattr(old_user, 'username') or not old_user.username:
                    # Generate username if not exists
                    old_user.username = old_user.name.lower().replace(' ', '_')
                
                # Set password
                old_user.set_password(default_password)
                old_user.is_active = True
                old_user.created_at = datetime.utcnow()
                
                converted_users.append(old_user)
                print(f"   ✅ Converted: {old_user.name} (username: {old_user.username})")
            
            db.session.commit()
            print(f"✅ Converted {len(converted_users)} users")
            
            # Step 4: Create default "Roommates" group
            print("\n🏠 Step 4: Creating default 'Roommates' group...")
            
            # Check if group already exists
            existing_group = Group.query.filter_by(name="Roommates").first()
            if existing_group:
                roommates_group = existing_group
                print("   ⏭️  'Roommates' group already exists")
            else:
                # Create the group
                roommates_group = Group(
                    name="Roommates",
                    description="Migrated from shared expense tracker",
                    creator_id=converted_users[0].id,  # First user becomes admin
                    invite_code=Group.generate_invite_code()
                )
                
                db.session.add(roommates_group)
                db.session.flush()  # Get group ID
                
                # Add all users to the group
                for user in converted_users:
                    roommates_group.add_member(user, role='admin' if user.id == converted_users[0].id else 'member')
                
                print(f"   ✅ Created 'Roommates' group with {len(converted_users)} members")
                print(f"   📋 Invite code: {roommates_group.invite_code}")
            
            db.session.commit()
            
            # Step 5: Migrate categories to group categories
            print("\n📂 Step 5: Migrating categories...")
            
            for category in existing_categories:
                if category.group_id is None and category.user_id is None:
                    # Migrate to group category
                    category.group_id = roommates_group.id
                    category.is_default = True
                    print(f"   ✅ Migrated category: {category.name}")
            
            db.session.commit()
            
            # Step 6: Migrate existing expenses to group
            print("\n💰 Step 6: Migrating existing expenses...")
            
            migrated_count = 0
            for expense in existing_expenses:
                if expense.group_id is None:  # Only migrate expenses not already assigned to a group
                    expense.group_id = roommates_group.id
                    migrated_count += 1
                    print(f"   ✅ Migrated expense: ${expense.amount} ({expense.category_obj.name})")
            
            db.session.commit()
            print(f"✅ Migrated {migrated_count} expenses to 'Roommates' group")
            
            # Step 7: Migrate recurring payments
            print("\n🔄 Step 7: Migrating recurring payments...")
            
            recurring_payments = RecurringPayment.query.all()
            migrated_recurring = 0
            
            for recurring in recurring_payments:
                if hasattr(recurring, 'group_id') and recurring.group_id is None:
                    recurring.group_id = roommates_group.id
                    migrated_recurring += 1
                    print(f"   ✅ Migrated recurring: ${recurring.amount} ({recurring.category_obj.name})")
            
            db.session.commit()
            print(f"✅ Migrated {migrated_recurring} recurring payments")
            
            # Step 8: Create personal categories for each user
            print("\n👤 Step 8: Creating personal categories for users...")
            
            personal_categories = [
                'Personal Food',
                'Personal Transportation', 
                'Personal Shopping',
                'Personal Entertainment',
                'Personal Healthcare',
                'Personal Other'
            ]
            
            for user in converted_users:
                for cat_name in personal_categories:
                    # Check if category already exists
                    existing_cat = Category.query.filter_by(
                        name=cat_name, 
                        user_id=user.id
                    ).first()
                    
                    if not existing_cat:
                        category = Category(
                            name=cat_name,
                            user_id=user.id,
                            is_default=False
                        )
                        db.session.add(category)
                
                print(f"   ✅ Created personal categories for {user.name}")
            
            db.session.commit()
            
            # Step 9: Summary and next steps
            print("\n🎉 Migration completed successfully!")
            print("\n📋 Summary:")
            print(f"   • Converted {len(converted_users)} users to authenticated accounts")
            print(f"   • Created 'Roommates' group with invite code: {roommates_group.invite_code}")
            print(f"   • Migrated {len(existing_categories)} categories")
            print(f"   • Migrated {migrated_count} expenses")
            print(f"   • Migrated {migrated_recurring} recurring payments")
            
            print("\n⚠️  IMPORTANT NEXT STEPS:")
            print("   1. All users have been given the temporary password: 'welcome123'")
            print("   2. Users should log in and change their passwords immediately")
            print("   3. Users may need to update their email addresses")
            print("   4. Share the group invite code with roommates who need access")
            print("   5. Test the new system thoroughly before going live")
            
            print("\n🔐 Login Information:")
            for user in converted_users:
                print(f"   • Username: {user.username}")
                print(f"     Email: {user.email}")
                print(f"     Temp Password: welcome123")
                print()
            
            print("✅ Migration complete! Your expense tracker is now multi-user enabled.")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Migration failed with error: {e}")
            print("\n📋 Troubleshooting tips:")
            print("   1. Make sure your database is backed up")
            print("   2. Check that your models.py file is updated")
            print("   3. Verify database connection settings")
            print("   4. Try running the migration again")
            import traceback
            traceback.print_exc()
            return False
    
    return True

def create_sample_data():
    """Create sample data for testing (optional)"""
    
    print("\n🎯 Creating sample data for testing...")
    
    app = create_app()
    with app.app_context():
        try:
            # Create test user if doesn't exist
            test_user = User.query.filter_by(username='testuser').first()
            if not test_user:
                test_user = User(
                    name='Test User',
                    username='testuser',
                    email='test@example.com'
                )
                test_user.set_password('testpass123')
                db.session.add(test_user)
                db.session.commit()
                print(f"   ✅ Created test user: testuser / testpass123")
            
            # Create test group
            test_group = Group.query.filter_by(name='Test Group').first()
            if not test_group:
                test_group = Group(
                    name='Test Group',
                    description='A test group for development',
                    creator_id=test_user.id,
                    invite_code=Group.generate_invite_code()
                )
                db.session.add(test_group)
                db.session.flush()
                
                test_group.add_member(test_user, role='admin')
                db.session.commit()
                print(f"   ✅ Created test group with invite code: {test_group.invite_code}")
            
            print("✅ Sample data created")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Failed to create sample data: {e}")

if __name__ == '__main__':
    print("🔄 Expense Tracker Database Migration")
    print("=====================================")
    
    # Ask for confirmation
    response = input("\nThis will migrate your existing data to the new multi-user system.\nDo you want to continue? (yes/no): ").lower().strip()
    
    if response in ['yes', 'y']:
        success = migrate_database()
        
        if success:
            # Ask if they want sample data
            sample_response = input("\nWould you like to create sample test data? (yes/no): ").lower().strip()
            if sample_response in ['yes', 'y']:
                create_sample_data()
        
        print("\n🚀 Migration process complete!")
        print("   Remember to:")
        print("   • Update your requirements.txt with new dependencies")
        print("   • Test the new authentication system")
        print("   • Have users change their temporary passwords")
        
    else:
        print("Migration cancelled.")
        print("💡 Tip: Make sure to backup your database before running the migration!")