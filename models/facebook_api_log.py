from database_init import db
from datetime import datetime


class FacebookApiLog(db.Model):
    __tablename__ = "facebook_api_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deployed_app_id = db.Column(
        db.Integer, db.ForeignKey("deployed_app.id"), nullable=False
    )
    api_endpoint = db.Column(db.String(255), nullable=False)
    called_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Thông tin lỗi
    status_code = db.Column(db.Integer, nullable=True)
    error_code = db.Column(db.Integer, nullable=True)
    error_subcode = db.Column(db.Integer, nullable=True)
    message = db.Column(db.Text, nullable=True)

    deployed_app = db.relationship(
        "DeployedApp", backref=db.backref("api_logs", lazy=True)
    )
