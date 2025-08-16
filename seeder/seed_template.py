from models.template import Template
from database_init import db


def seed_template(app):
    """Seed 3 sample frontend templates."""
    with app.app_context():
        templates = [
            {
                "name": "Default Template",
                "description": "Sample template for company website",
                "sample_url": "skylinkny.asenanen2.com",
                "port": 3000,
                "backend": "https://tool-deploy.bmappp.com/",
                "country_code": "us",
                "priority": 50,
            },
            {
                "name": "Fashion Template",
                "description": "Fashion landing page template (vite)",
                "sample_url": "bmappp.com",
                "port": 5173,
                "backend": "https://tool-deploy.bmappp.com/",
                "country_code": "us",
                "priority": 1,
            },
            {
                "name": "Bất động sản",
                "description": "Template giới thiệu dự án bất động sản",
                "sample_url": "realestate.example.com",
                "port": 8330,
                "backend": "https://tool-deploy.bmappp.com/",
                "country_code": "vn",
                "priority": 10,
            },
            {
                "name": "Tạp hóa",
                "description": "Website bán tạp hóa, siêu thị mini",
                "sample_url": "grocery.example.com",
                "port": 8112,
                "backend": "https://tool-deploy.bmappp.com/",
                "country_code": "vn",
                "priority": 5,
            },
            {
                "name": "XKLD",
                "description": "Website giới thiệu công ty Esuhai và dịch vụ xuất khẩu lao động",
                "sample_url": "esuhai.example.com",
                "port": 8221,
                "backend": "https://tool-deploy.bmappp.com/",
                "country_code": "vn",
                "priority": 5,
            },
            {
                "name": "Du lịch",
                "description": "Website giới thiệu công ty Du lịch và dịch vụ du lịch",
                "sample_url": "esuhai.example.com",
                "port": 8441,
                "backend": "https://tool-deploy.bmappp.com/",
                "country_code": "vn",
                "priority": 6,
            },
        ]

        for tpl in templates:
            if not Template.query.filter_by(name=tpl["name"]).first():
                template = Template(
                    name=tpl["name"],
                    description=tpl["description"],
                    sample_url=tpl["sample_url"],
                    port=tpl["port"],
                    backend=tpl["backend"],
                    country_code=tpl["country_code"],
                    priority=tpl["priority"],
                )
                db.session.add(template)
                print(f"Success:  Đã tạo Template: {tpl['name']}")
            else:
                print(f"Warning:  Template '{tpl['name']}' đã tồn tại, bỏ qua.")

        db.session.commit()
