from database_init import db


class Template(db.Model):
    __tablename__ = "template"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sample_url = db.Column(
        db.String(255), nullable=False
    )  # Link demo/sample template (không cần ảnh)

    port = db.Column(db.Integer, nullable=False, default=3000)
    backend = db.Column(
        db.String(255), nullable=False, default="https://tool-deploy.bmappp.com/"
    )

    def __repr__(self):
        return f"<Template {self.name}>"
