from database_init import db

class CloudflareAccount(db.Model):
    __tablename__ = "cloudflare_account"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    api_token = db.Column(db.String(255), nullable=False)  # CLOUD_FLARE_TOKEN
    account_id = db.Column(db.String(64), nullable=True)   # CLOUDFLARE_ACCOUNT_ID

    # ✅ Nameserver được dùng chung cho tất cả domain thuộc tài khoản này
    ns1 = db.Column(db.String(255), nullable=True)
    ns2 = db.Column(db.String(255), nullable=True)

    # Quan hệ 1-n: một tài khoản quản lý nhiều domain
    domains = db.relationship("Domain", back_populates="cloudflare_account")

    def __repr__(self):
        return f"<CloudflareAccount {self.name}>"
