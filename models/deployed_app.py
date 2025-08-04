from database_init import db
from datetime import datetime
from util.constant import DEPLOYED_APP_STATUS

class DeployedApp(db.Model):
    __tablename__ = "deployed_app"
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey("domain.id"), nullable=False)
    subdomain = db.Column(db.String(255), nullable=True)  # subdomain/app.example.com
    env = db.Column(db.Text)  # lưu biến ENV dạng text hoặc JSON
    port = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.String(50), default=DEPLOYED_APP_STATUS.deploying.value
    ) 
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    activated_at = db.Column(
        db.DateTime, default=datetime.utcnow
    )
    deactivated_at = db.Column(
        db.DateTime, default=None, nullable=True
    )
    sync_at = db.Column(
        db.DateTime, default=datetime.utcnow
    )

    server = db.relationship("Server", back_populates="deployed_apps")
    domain = db.relationship("Domain", back_populates="deployed_apps")

    def __repr__(self):
        return f"<DeployedApp {self.subdomain or ''} @ {self.domain_id}>"
