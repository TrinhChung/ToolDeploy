import json
from models.product import Product
from database_init import db
import os

def seed_product(app):
    """Seed all products from ./data/product.json into database."""
    data_file = os.path.join(os.path.dirname(__file__), "./data/product.json")
    # Đảm bảo đường dẫn đúng
    data_file = os.path.abspath(data_file)

    # Đọc file product.json
    with open(data_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    with app.app_context():
        added_count = 0
        for prod in products:
            # Kiểm tra nếu sản phẩm đã tồn tại (theo title)
            if not Product.query.filter_by(title=prod['title']).first():
                product = Product(
                    title=prod['title'],
                    image=prod['image'],
                    category=prod['category'],
                    price=prod['price'],
                    popularity=prod['popularity'],
                    stock=prod['stock'],
                    description=prod['description'],
                    detail=prod['detail'],
                    delivery_detail=prod['delivery_detail'],
                )
                db.session.add(product)
                added_count += 1
        if added_count > 0:
            db.session.commit()
            print(f"✅ Đã thêm {added_count} sản phẩm mới.")
        else:
            print("⚠️ Không có sản phẩm mới để thêm (đã tồn tại hết).")