from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Group

# A separate blueprint for user-facing routes keeps the code organized.
income_bp = Blueprint('income_routes', __name__, url_prefix='/income')

@income_bp.route('/view/<int:group_id>')
@login_required
def view_income_for_group(group_id):
    """
    Provides a dedicated URL for accessing the income section of a group.

    Since the income management UI is a modal on the main tracker page,
    this route simply verifies access and redirects the user to that page.
    """
    group = Group.query.get_or_404(group_id)

    # Verify that the current user is a member of the group before redirecting.
    if current_user not in group.members:
        flash('You are not authorized to view income for this group.', 'error')
        # Redirect to a general page, like a dashboard (assuming it exists).
        return redirect(url_for('dashboard.home'))

    # Redirect to the main group tracker page, which contains the income modal.
    # The 'expenses.group_tracker' endpoint is inferred from your 'management.html' template.
    return redirect(url_for('expenses.group_tracker', group_id=group.id))