from database_init import db

class Company(db.Model):
    __tablename__ = "company"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)                 # Tên công ty
    address = db.Column(db.Text, nullable=True)                      # Địa chỉ (có thể dài)
    hotline = db.Column(db.String(30), nullable=True)                # Số điện thoại
    email = db.Column(db.String(255), nullable=True)                 # Email liên hệ
    license_no = db.Column(db.String(100), nullable=True)            # Số giấy phép kinh doanh
    google_map_embed = db.Column(db.Text, nullable=True)             # Mã nhúng Google Map hoặc URL
    logo_url = db.Column(db.String(255), nullable=True)              # Link logo
    footer_text = db.Column(db.Text, nullable=True)                  # Nội dung hiển thị footer
    description = db.Column(db.Text, nullable=True)                  # Mô tả về công ty (nếu cần)
    note = db.Column(db.Text, nullable=True)                         # Trường ghi chú mở rộng
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='companies')
     
    # Liên kết tới các website (1-n)
    websites = db.relationship('Website', back_populates='company')

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}')>"
