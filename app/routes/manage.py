
from flask import Blueprint, render_template

from models import Group

manage_bp = Blueprint("manage", __name__)

@manage_bp.route("/manage/<int:group_id>")
def management(group_id):
    group = Group.query.get_or_404(group_id)
    return render_template("manage.html", group=group)
