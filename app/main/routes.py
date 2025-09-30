from flask import render_template
from flask_login import current_user
from . import main_bp

@main_bp.route("/")
def index():
    return render_template("main/index.html", user=current_user if current_user.is_authenticated else None)
