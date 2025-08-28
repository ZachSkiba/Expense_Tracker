
from flask import Blueprint, render_template

manage_bp = Blueprint("manage", __name__)

@manage_bp.route("/manage")
def management():
    return render_template("manage.html")
