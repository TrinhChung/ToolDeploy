from flask import Blueprint, render_template

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def home():
    return "<h1>Welcome to Home Page</h1>"

@home_bp.route('/terms')
def terms():
    return "<h1>Terms and Conditions</h1>"

@home_bp.route('/polices')
def polices():
    return "<h1>Privacy Policies</h1>"
