import json
from models.user_fe import UserFE
from database_init import db
import os


def seed_user_fe(app):
    """Seed user FE data from ./data/user_fe.json into database."""
    data_file = os.path.join(os.path.dirname(__file__), "./data/user_fe.json")
    data_file = os.path.abspath(data_file)

    with open(data_file, "r", encoding="utf-8") as f:
        users = json.load(f)

    with app.app_context():
        added_count = 0
        for u in users:
            if not UserFE.query.filter_by(email=u["email"]).first():
                user = UserFE(
                    name=u["name"],
                    lastname=u.get("lastname"),
                    email=u["email"],
                    password=u["password"],
                    phone=u.get("phone"),
                    address=u.get("address"),
                )
                db.session.add(user)
                added_count += 1
        if added_count > 0:
            db.session.commit()
            print(f"✅ Đã thêm {added_count} user FE mới.")
        else:
            print("⚠️ Không có user FE mới để thêm (đã tồn tại hết).")
