# app/routes/tracker/budgeting/__init__.py

"""Budget analytics routes"""

from flask import Blueprint

# Create the blueprint
budgeting_bp = Blueprint(
    'budgeting',
    __name__,
    url_prefix='/group/<int:group_id>/budgeting'
)

# Import routes after blueprint creation to avoid circular imports
from . import analytics, api