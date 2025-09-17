"""
Migration script to convert legacy expense tracker to proper group system
Run this once to migrate your current legacy expenses to a group
"""

from models import db, User, Group, Category, Expense, RecurringPayment
from datetime import datetime

def migrate_legacy_to_group():
    """Convert legacy expenses and system to a proper group"""
    
    print("🔄 Starting legacy to group migration...")
    
    # Step 1: Create the legacy group
    legacy_group = Group.query.filter_by(name="Roommates Legacy").first()
    
    if not legacy_group:
        legacy_group = Group(
            name="Roommates Legacy",
            description="Converted from legacy shared expense tracker",
            creator_id=5,  # Zach's ID - adjust as needed
            invite_code=Group.generate_invite_code(),
            created_at=datetime.utcnow()
        )
        db.session.add(legacy_group)
        db.session.flush()  # Get the group ID
        print(f"✅ Created legacy group with ID: {legacy_group.id}")
    else:
        print(f"✅ Legacy group already exists with ID: {legacy_group.id}")
    
    # Step 2: Add legacy users to the group
    legacy_user_ids = [5, 6, 7, 8, 9]  # Zach, Jake, Nick, Aaron, Jakub
    
    for user_id in legacy_user_ids:
        user = User.query.get(user_id)
        if user:
            if user not in legacy_group.members:
                role = 'admin' if user_id == 5 else 'member'  # Make Zach admin
                legacy_group.add_member(user, role=role)
                print(f"✅ Added {user.name} to legacy group as {role}")
            else:
                print(f"⏭️  {user.name} already in legacy group")
        else:
            print(f"⚠️  User ID {user_id} not found")
    
    # Step 3: Migrate categories to the group
    legacy_categories = Category.query.filter_by(
        group_id=None, 
        user_id=None, 
        is_default=True
    ).all()
    
    print(f"🏷️  Found {len(legacy_categories)} legacy categories to migrate")
    
    for category in legacy_categories:
        # Create group-specific copy
        group_category = Category.query.filter_by(
            name=category.name,
            group_id=legacy_group.id
        ).first()
        
        if not group_category:
            group_category = Category(
                name=category.name,
                group_id=legacy_group.id,
                is_default=True
            )
            db.session.add(group_category)
            print(f"✅ Migrated category: {category.name}")
    
    db.session.flush()
    
    # Step 4: Update existing expenses to use the legacy group
    legacy_expenses = Expense.query.filter_by(group_id=None).all()
    print(f"💰 Found {len(legacy_expenses)} legacy expenses to migrate")
    
    for expense in legacy_expenses:
        # Find the corresponding group category
        group_category = Category.query.filter_by(
            name=expense.category_obj.name,
            group_id=legacy_group.id
        ).first()
        
        if group_category:
            expense.group_id = legacy_group.id
            expense.category_id = group_category.id
            print(f"✅ Migrated expense: ${expense.amount} - {expense.category_obj.name}")
        else:
            print(f"⚠️  Could not find group category for: {expense.category_obj.name}")
    
    # Step 5: Update recurring payments to use the legacy group
    recurring_payments = RecurringPayment.query.filter_by(group_id=None).all()
    print(f"🔄 Found {len(recurring_payments)} recurring payments to migrate")
    
    for payment in recurring_payments:
        # Find the corresponding group category
        group_category = Category.query.filter_by(
            name=payment.category_obj.name,
            group_id=legacy_group.id
        ).first()
        
        if group_category:
            payment.group_id = legacy_group.id
            payment.category_id = group_category.id
            print(f"✅ Migrated recurring payment: ${payment.amount} - {payment.category_obj.name}")
        else:
            print(f"⚠️  Could not find group category for recurring payment: {payment.category_obj.name}")
    
    # Step 6: Commit all changes
    try:
        db.session.commit()
        print("✅ Migration completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Legacy group ID: {legacy_group.id}")
        print(f"   - Group members: {legacy_group.get_member_count()}")
        print(f"   - Invite code: {legacy_group.invite_code}")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Migration failed: {e}")
        raise

def verify_migration():
    """Verify that the migration worked correctly"""
    
    print("\n🔍 Verifying migration...")
    
    legacy_group = Group.query.filter_by(name="Roommates Legacy").first()
    if not legacy_group:
        print("❌ Legacy group not found!")
        return False
    
    print(f"✅ Legacy group found: {legacy_group.name} (ID: {legacy_group.id})")
    print(f"✅ Members: {legacy_group.get_member_count()}")
    
    # Check expenses
    group_expenses = Expense.query.filter_by(group_id=legacy_group.id).count()
    orphan_expenses = Expense.query.filter_by(group_id=None).count()
    
    print(f"✅ Group expenses: {group_expenses}")
    print(f"⚠️  Orphan expenses (should be 0): {orphan_expenses}")
    
    # Check categories
    group_categories = Category.query.filter_by(group_id=legacy_group.id).count()
    print(f"✅ Group categories: {group_categories}")
    
    # Check recurring payments
    group_recurring = RecurringPayment.query.filter_by(group_id=legacy_group.id).count()
    orphan_recurring = RecurringPayment.query.filter_by(group_id=None).count()
    
    print(f"✅ Group recurring payments: {group_recurring}")
    print(f"⚠️  Orphan recurring payments (should be 0): {orphan_recurring}")
    
    return True

if __name__ == "__main__":
    # Run the migration
    migrate_legacy_to_group()
    verify_migration()