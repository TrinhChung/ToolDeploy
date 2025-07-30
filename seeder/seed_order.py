import json
import os
from datetime import datetime
from models.order import Order
from models.order_item import OrderItem
from models.user_fe import UserFE
from models.product import Product
from database_init import db


def _parse_date(date_str):
    """Chuyển chuỗi thời gian thành datetime."""
    if not date_str:
        return None
    try:
        if 'T' in date_str:
            if date_str.endswith('Z'):
                date_str = date_str[:-1]
            return datetime.fromisoformat(date_str)
        return datetime.strptime(date_str, "%m/%d/%Y")
    except Exception:
        return None


def seed_orders(app):
    """Seed orders và order items từ ./data/order.json vào database."""
    data_file = os.path.join(os.path.dirname(__file__), "./data/order.json")
    data_file = os.path.abspath(data_file)

    with open(data_file, "r", encoding="utf-8") as f:
        orders = json.load(f)

    with app.app_context():
        added_count = 0
        for od in orders:
            user = UserFE.query.filter_by(email=od.get("user", {}).get("email")).first()
            if not user:
                continue
            order_date = _parse_date(od.get("orderDate"))
            exists = Order.query.filter_by(user_fe_id=user.id, order_date=order_date).first()
            if exists:
                continue
            order = Order(
                user_fe_id=user.id,
                order_status=od.get("orderStatus", "Processing"),
                order_date=order_date,
                subtotal=od.get("subtotal", 0),
                shipping_address=od.get("data", {}).get("address"),
                phone=od.get("data", {}).get("phone"),
                payment_type=od.get("data", {}).get("paymentType"),
            )
            db.session.add(order)
            db.session.flush()
            for item in od.get("products", []):
                prod = Product.query.filter_by(title=item.get("title")).first()
                if not prod:
                    continue
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=prod.id,
                    quantity=item.get("quantity", 1),
                    price=item.get("price", 0),
                    size=item.get("size"),
                    color=item.get("color"),
                    popularity=item.get("popularity"),
                    stock=item.get("stock"),
                )
                db.session.add(order_item)
            added_count += 1
        if added_count > 0:
            db.session.commit()
            print(f"✅ Đã thêm {added_count} đơn hàng mới.")
        else:
            print("⚠️ Không có đơn hàng mới để thêm (đã tồn tại hết).")
