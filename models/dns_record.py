from database_init import db


class DNSRecord(db.Model):
    __tablename__ = "dns_record"
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("domain.id"), nullable=False)
    record_id = db.Column(
        db.String(64), nullable=True
    )  # Cloudflare DNS record ID (quan trọng để sửa/xóa)
    record_type = db.Column(db.String(50), nullable=False)  # A, CNAME, TXT,...
    name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    ttl = db.Column(db.Integer, default=3600, nullable=False)
    proxied = db.Column(db.Boolean, default=False)
    domain = db.relationship("Domain", back_populates="dns_records")

    def __repr__(self):
        return f"<DNSRecord {self.name} ({self.record_type})>"
