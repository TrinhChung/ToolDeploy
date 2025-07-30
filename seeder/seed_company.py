# seeder/seed_company.py
import os
from dotenv import load_dotenv
from models.company import Company
from models.user import User
from database_init import db

load_dotenv()

def seed_companies(app):
    # Đọc thông tin user từ biến môi trường (giống seed_user)
    seed_username = os.getenv("ADMIN_USERNAME")   # hoặc đổi thành SEED_USERNAME nếu muốn tách biệt
    seed_email = os.getenv("ADMIN_EMAIL")         # tuỳ bạn

    companies = [
        {
            "name": "FREIGHTCAN LLC",
            "address": """CARGO BLDG. 75, N. HANGER ROAD
SUITE 205B, JFK INT’L AIRPORT
JAMAICA, NY 11430
UNITED STATES""",
            "hotline": "718-995-9594",
            "email": "info@freightcanllc.asenanen.com",
            "license_no": "019229",
            "google_map_embed": """
<iframe src="https://www.google.com/maps?q=JFK+Cargo+Building+75&output=embed" width="600" height="300" style="border:0;" allowfullscreen="" loading="lazy"></iframe>
""",
            "logo_url": "/static/images/logo/fashion.svg",
            "footer_text": "",
            "description": "FreightCan LLC - chuyên vận chuyển hàng hóa quốc tế qua sân bay JFK.",
        },
        # Thêm các công ty khác ở đây nếu muốn
    ]

    with app.app_context():
        # Lấy user từ username/email env
        user = None
        if seed_username:
            user = User.query.filter_by(username=seed_username).first()
        if not user and seed_email:
            user = User.query.filter_by(email=seed_email).first()
        if not user:
            print("❌ Không tìm thấy user để gán cho company. Kiểm tra .env và seed user trước!")
            return

        for data in companies:
            data_with_user = dict(data)
            data_with_user["user_id"] = user.id
            if not Company.query.filter_by(name=data['name'], user_id=user.id).first():
                company = Company(**data_with_user)
                db.session.add(company)
                print(f"✅ Đã tạo company: {data['name']}")
            else:
                print(f"⚠️ Company '{data['name']}' đã tồn tại cho user này, bỏ qua.")
        db.session.commit()
