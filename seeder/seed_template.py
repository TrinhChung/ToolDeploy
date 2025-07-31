from models.template import Template
from database_init import db


def seed_template(app):
    """Seed a sample frontend template."""
    with app.app_context():
        name = "Default Template"
        description = "Sample template for company website"
        sample_url = "smartrent.id.vn"
        port = 3000
        backend = "https://tool-deploy.bmappp.com/"

        if not Template.query.filter_by(name=name).first():
            template = Template(
                name=name,
                description=description,
                sample_url=sample_url,
                port=port,
                backend=backend,
            )
            db.session.add(template)
            db.session.commit()
            print(f"✅ Đã tạo Template: {name}")
        else:
            print("⚠️ Template đã tồn tại, bỏ qua.")
