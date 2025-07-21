# seeder/seed_user.py
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

from models.user import User
from database_init import db

load_dotenv()


def seed_admin_user(app):
    with app.app_context():
        username = os.getenv("ADMIN_USERNAME")
        email = os.getenv("ADMIN_EMAIL")
        raw_password = os.getenv("ADMIN_PASSWORD")

        if not username or not email or not raw_password:
            print("❌ Thiếu ADMIN_USERNAME, ADMIN_EMAIL hoặc ADMIN_PASSWORD trong .env")
            return

        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(raw_password),
                is_active=True,
                is_admin=True,
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Đã tạo user admin: {username}")
        else:
            print("⚠️ User admin đã tồn tại, bỏ qua.")
