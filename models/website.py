from database_init import db
from util.constant import DEPLOYED_APP_STATUS

class Website(db.Model):
    __tablename__ = "website"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    domain_id = db.Column(
        db.Integer, db.ForeignKey("domain.id"), nullable=False
    )  # <--- sửa lại
    template_id = db.Column(db.Integer, db.ForeignKey("template.id"), nullable=True)
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)
    static_page_link = db.Column(db.Text, nullable=True)
    note = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(50), default=DEPLOYED_APP_STATUS.deploying.value) 
    company = db.relationship("Company", back_populates="websites")
    domain = db.relationship("Domain", back_populates="websites")  # <--- thêm dòng này
    template = db.relationship("Template")
    server = db.relationship("Server")
    user = db.relationship("User", back_populates="websites")
