from database_init import db


class Domain(db.Model):
    __tablename__ = "domain"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)  # example.com
    zone_id = db.Column(db.String(255), nullable=True)  # Cloudflare Zone ID
    status = db.Column(
        db.String(50), default="pending", nullable=False
    ) 
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", back_populates="domains")
    dns_records = db.relationship("DNSRecord", back_populates="domain", lazy=True)
    deployed_apps = db.relationship("DeployedApp", back_populates="domain", lazy=True)
    cloudflare_account_id = db.Column(db.Integer, db.ForeignKey("cloudflare_account.id"), nullable=True)
    cloudflare_account = db.relationship("CloudflareAccount", back_populates="domains")
    websites = db.relationship(
        "Website", back_populates="domain", lazy=True
    )  # <--- thêm dòng này

    def __repr__(self):
        return f"<Domain {self.name}>"
