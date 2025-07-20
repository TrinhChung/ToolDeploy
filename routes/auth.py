# routes.auth.py
from flask import (
    Blueprint,
)

from dotenv import load_dotenv

auth_bp = Blueprint("auth", __name__)

load_dotenv()


# Route to show the login page
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    return "<h1>Login</h1>"


# Route to handle logout
@auth_bp.route("/logout")
def logout():
    return "<h1>Login</h1>"
