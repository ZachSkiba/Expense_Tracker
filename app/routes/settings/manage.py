
from flask import Blueprint, render_template

from models import Group

manage_bp = Blueprint("manage", __name__, url_prefix='/settings')

@manage_bp.route("/<int:group_id>")
def settings(group_id):
    group = Group.query.get_or_404(group_id)
    return render_template("settings/settings.html", group=group)
