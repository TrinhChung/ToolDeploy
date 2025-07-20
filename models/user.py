from database_init import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=False)  # Mới đăng ký thì chưa active
    is_admin = db.Column(db.Boolean, default=False)  # Quyền admin, mặc định user thường

    # Optional: property cho Flask-Login
    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True

    # Flask-Login mặc định dùng thuộc tính is_active, nếu muốn override:
    # def is_active(self):
    #     return self.is_active
