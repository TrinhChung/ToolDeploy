from database_init import db

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    user_fe_id = db.Column(db.Integer, db.ForeignKey('user_fe.id'), nullable=False)
    order_status = db.Column(db.String(50), default="Processing")
    order_date = db.Column(db.DateTime, server_default=db.func.now())
    subtotal = db.Column(db.Integer, nullable=False)
    shipping_address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    payment_type = db.Column(db.String(30), nullable=True)
    note = db.Column(db.Text, nullable=True)

    user_fe = db.relationship("UserFE", back_populates="orders")
    order_items = db.relationship("OrderItem", back_populates="order", lazy=True)

    def __repr__(self):
        return f"<Order {self.id} - UserFE {self.user_fe_id}>"