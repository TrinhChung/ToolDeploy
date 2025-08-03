from database_init import db


class WebDomainVerification(db.Model):
    __tablename__ = "web_domain_verification"
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(
        db.Integer, db.ForeignKey("website.id"), nullable=False
    )
    txt_value = db.Column(db.String(255), nullable=False)  # Bản ghi TXT hiện tại
    create_count = db.Column(db.Integer, default=1)  # Số lần tạo/cập nhật TXT

    # Liên kết ngược với DeployedApp (truy cập: app.verification)
    website = db.relationship(
        "Website", backref=db.backref("web_verification", uselist=False)
    )
