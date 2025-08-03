from models.template import Template
from database_init import db


def seed_template(app):
    """Seed 2 sample frontend templates."""
    with app.app_context():
        templates = [
            {
                "name": "Default Template",
                "description": "Sample template for company website",
                "sample_url": "skylinkny.asenanen2.com",
                "port": 3000,
                "backend": "https://tool-deploy.bmappp.com/",
            },
            {
                "name": "Fashion Template",
                "description": "Fashion landing page template (vite)",
                "sample_url": "bmappp.com",
                "port": 5173,
                "backend": "https://tool-deploy.bmappp.com/",
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
                )
                db.session.add(template)
                print(f"✅ Đã tạo Template: {tpl['name']}")
            else:
                print(f"⚠️ Template '{tpl['name']}' đã tồn tại, bỏ qua.")

        db.session.commit()
