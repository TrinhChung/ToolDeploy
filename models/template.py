from datetime import datetime
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

    # Mã quốc gia (ISO 2 chữ: ví dụ 'vn', 'us')
    country_code = db.Column(db.String(2), nullable=True, default="vn")

    # Độ ưu tiên (số nguyên, càng lớn càng ưu tiên cao)
    priority = db.Column(db.Integer, nullable=True, default=0)

    # Soft delete: ngày giờ xóa (NULL = chưa xóa)
    deleted_at = db.Column(db.DateTime, nullable=True, default=None)

    def __repr__(self):
        return f"<Template {self.name}>"

    def soft_delete(self):
        """Đánh dấu xóa mềm"""
        self.deleted_at = datetime.utcnow()
        db.session.commit()

    def restore(self):
        """Khôi phục bản ghi bị xóa mềm"""
        self.deleted_at = None
        db.session.commit()
