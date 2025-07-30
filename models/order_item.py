from database_init import db

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    size = db.Column(db.String(20), nullable=True)
    color = db.Column(db.String(30), nullable=True)
    popularity = db.Column(db.Integer, nullable=True)
    stock = db.Column(db.Integer, nullable=True)

    order = db.relationship("Order", back_populates="order_items")
    product = db.relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.id} - Order {self.order_id} - Product {self.product_id}>"