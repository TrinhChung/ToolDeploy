from database_init import db

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    image = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(120), nullable=True)
    price = db.Column(db.Integer, nullable=False)
    popularity = db.Column(db.Integer, nullable=True, default=0)
    stock = db.Column(db.Integer, nullable=True, default=0)

    # Thêm các trường mới
    description = db.Column(db.Text, nullable=True)
    detail = db.Column(db.Text, nullable=True)
    delivery_detail = db.Column(db.Text, nullable=True)

    order_items = db.relationship("OrderItem", back_populates="product", lazy=True)

    def __repr__(self):
        return f"<Product {self.id} - {self.title}>"
