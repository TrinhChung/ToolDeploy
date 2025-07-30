from database_init import db

# User FE (Khách hàng - đã trình bày ở trên)
class UserFE(db.Model):
    __tablename__ = 'user_fe'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    lastname = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)
    orders = db.relationship("Order", back_populates="user_fe", lazy=True)

    def __repr__(self):
        return f"<UserFE {self.id} - {self.email}>"