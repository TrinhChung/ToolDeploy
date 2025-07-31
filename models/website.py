from database_init import db


class Website(db.Model):
    __tablename__ = "website"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    dns_record_id = db.Column(
        db.Integer, db.ForeignKey("dns_record.id"), nullable=False
    )
    template_id = db.Column(db.Integer, db.ForeignKey("template.id"), nullable=True)
    server_id = db.Column(
        db.Integer, db.ForeignKey("server.id"), nullable=False
    )  # <--- Thêm dòng này
    static_page_link = db.Column(db.Text, nullable=True)
    note = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    company = db.relationship("Company", back_populates="websites")
    dns_record = db.relationship("DNSRecord")
    template = db.relationship("Template")
    server = db.relationship(
        "Server"
    )  # <--- Thêm dòng này nếu muốn truy cập server từ website

    user = db.relationship("User", back_populates="websites")
