from flask import Blueprint, render_template
bp = Blueprint("public_routes", __name__)

@bp.route("/")
def home():
    return render_template("public/home.html")
