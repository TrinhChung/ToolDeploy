from flask import Flask, session, redirect, url_for, flash, request
from flask_migrate import Migrate
from database_init import db
from dotenv import load_dotenv
import os
import secrets
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
from log import setup_logging

from util.until import format_datetime

# Import tất cả các mô hình


load_dotenv()

migrate = Migrate()


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
            phone_number=os.getenv("PHONE_NUMBER", "07084773484")
        )

    # Cấu hình logging
    setup_logging()

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    # Cấu hình thời gian sống của session
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)

    # Thiết lập cookie bảo mật
    app.config["SESSION_COOKIE_HTTPONLY"] = (
        True  # Chỉ có thể truy cập session từ phía server
    )
    app.config["SESSION_COOKIE_SECURE"] = (
        True  # Chỉ gửi cookie qua HTTPS (nếu triển khai trên server có HTTPS)
    )
    app.config["SESSION_COOKIE_SAMESITE"] = (
        "Lax"  # Xác định phạm vi của cookie, tránh chia sẻ với các trang web khác
    )

    csrf = CSRFProtect(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql://{os.getenv('USER_DB')}:{os.getenv('PASSWORD_DB')}@{os.getenv('ADDRESS_DB')}/{os.getenv('NAME_DB')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.jinja_env.filters["datetimeformat"] = format_datetime

    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(minutes=30)

    db.init_app(app)
    migrate.init_app(app, db)

    from routes.home import home_bp
    from routes.auth import auth_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)

    @app.before_request
    def require_login():
        allowed_routes = [
            "auth.login",
            "auth.logout",
            "home.polices",
            "home.terms",
            "home.home",
            "video.serve_video",
            "static",
        ]
        if "facebook_user_id" not in session and request.endpoint not in allowed_routes:
            flash("You need to log in to access this page.", "danger")
            return redirect(url_for("auth.login"))

    @app.template_filter('format_currency')
    def format_currency(value, currency="USD"):
        if isinstance(value, (int, float)):
            return f"{value:,.2f} {currency}"
        return value

    return app


if __name__ == "__main__":
    app = create_app()
    # Flask-Migrate sẽ tự động xử lý migrations
    with app.app_context():
        db.create_all()

    app.run(debug=True)
