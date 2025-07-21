from flask import Flask, session, redirect, url_for, flash, request
from flask_migrate import Migrate
from database_init import db
from dotenv import load_dotenv
import os
import secrets
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
from log import setup_logging
from flask_login import LoginManager, current_user
from seeder.seed_user import seed_admin_user

from util.until import format_datetime
from models.user import User
from models.domain import Domain
from models.dns_record import DNSRecord
from models.server import Server
from models.deployed_app import DeployedApp

load_dotenv()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # Tên endpoint của route login


def create_app():
    app = Flask(__name__, static_url_path="/static")

    @app.context_processor
    def inject_common_env():
        return dict(
            app_name=os.getenv("APP_NAME", "TOOL DEPLOY"),
            contact_email=os.getenv("EMAIL", "chungtrinh2k2@gmail.com"),
            address=os.getenv(
                "ADDRESS", "147 Thái Phiên, Phường 9,Quận 11, TP.HCM, Việt Nam"
            ),
            dns_web=os.getenv("DNS_WEB", "smartrent.id.vn"),
            tax_number=os.getenv("TAX_NUMBER", "0318728792"),
            phone_number=os.getenv("PHONE_NUMBER", "07084773484"),
        )

    # Cấu hình logging
    setup_logging()

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql://{os.getenv('USER_DB')}:{os.getenv('PASSWORD_DB')}@{os.getenv('ADDRESS_DB')}/{os.getenv('NAME_DB')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.jinja_env.filters["datetimeformat"] = format_datetime
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(minutes=30)

    csrf = CSRFProtect(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Định nghĩa user_loader cho Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.home import home_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.server import server_bp
    from routes.domain import domain_bp
    from routes.dns import dns_bp
    from routes.deployed_app import deployed_app_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(server_bp)
    app.register_blueprint(domain_bp)
    app.register_blueprint(dns_bp)
    app.register_blueprint(deployed_app_bp)

    # Kiểm soát truy cập: dùng Flask-Login, không cần kiểm tra "facebook_user_id" nữa
    @app.before_request
    def require_login():
        allowed_routes = [
            "auth.login",
            "auth.register",
            "auth.logout",
            "home.polices",
            "home.terms",
            "home.home",
            "video.serve_video",
            "static",
        ]
        if not current_user.is_authenticated and request.endpoint not in allowed_routes:
            flash("You need to log in to access this page.", "danger")
            return redirect(url_for("auth.login"))

    @app.template_filter("format_currency")
    def format_currency(value, currency="USD"):
        if isinstance(value, (int, float)):
            return f"{value:,.2f} {currency}"
        return value

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_admin_user(app)
    app.run(debug=False)
