from models import db, Category

class CategoryService:
    
    @staticmethod
    def get_all():
        """Get all categories"""
        return Category.query.all()
    
    @staticmethod
    def get_all_data():
        """Get all categories as list of dicts for JSON/template use"""
        categories = Category.query.all()
        return [{'id': c.id, 'name': c.name} for c in categories]
    
    @staticmethod
    def create_category(name):
        """
        Create a new category
        
        Returns:
            tuple: (category_object, error_message)
        """
        name = name.strip()
        if not name:
            return None, "Name cannot be empty"
        
        if Category.query.filter_by(name=name).first():
            return None, f"Category '{name}' already exists"
        
        try:
            new_category = Category(name=name)
            db.session.add(new_category)
            db.session.commit()
            return new_category, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    @staticmethod
    def can_delete_category(category_id):
        """
        Check if category can be safely deleted
        
        Returns:
            tuple: (can_delete_boolean, error_message)
        """
        category = Category.query.get_or_404(category_id)
        
        if category.expenses:
            return False, f"Cannot delete category '{category.name}' because it has existing expenses."
        
        return True, None
    
    @staticmethod
    def delete_category(category_id):
        """
        Delete category after validation
        
        Returns:
            tuple: (success_boolean, error_message)
        """
        try:
            can_delete, reason = CategoryService.can_delete_category(category_id)
            if not can_delete:
                return False, reason
            
            category = Category.query.get_or_404(category_id)
            db.session.delete(category)
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)