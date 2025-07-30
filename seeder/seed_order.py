import json
import os
from datetime import datetime
from models.order import Order
from models.order_item import OrderItem
from models.user_fe import UserFE
from models.product import Product
from database_init import db


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        if "T" in date_str:
            if date_str.endswith("Z"):
                date_str = date_str[:-1]
            return datetime.fromisoformat(date_str)
        return datetime.strptime(date_str, "%m/%d/%Y")
    except Exception:
        return None


def seed_orders(app):
    """Seed orders và order items từ ./data/order.json vào database, tránh trùng lặp."""
    data_file = os.path.join(os.path.dirname(__file__), "./data/order.json")
    data_file = os.path.abspath(data_file)

    with open(data_file, "r", encoding="utf-8") as f:
        orders = json.load(f)

        added_count = 0
        for od in orders:
            user = UserFE.query.filter_by(email=od.get("user", {}).get("email")).first()
            if not user:
                continue
            order_date = _parse_date(od.get("orderDate"))
            subtotal = od.get("subtotal", 0)
            phone = od.get("data", {}).get("phone")
            shipping_address = od.get("data", {}).get("address")
            exists_order = Order.query.filter_by(
                user_fe_id=user.id,
                subtotal=subtotal,
                phone=phone,
                shipping_address=shipping_address
            ).first()
            if exists_order:
                continue  # Đã có order này rồi
            order_date = _parse_date(od.get("orderDate"))
            order = Order(
                user_fe_id=user.id,
                order_status=od.get("orderStatus", "Processing"),
                order_date=order_date,
                subtotal=subtotal,
                shipping_address=shipping_address,
                phone=phone,
                payment_type=od.get("data", {}).get("paymentType"),
            )
            db.session.add(order)
            db.session.flush()  # Lấy order.id

            for item in od.get("products", []):
                prod = Product.query.filter_by(title=item.get("title")).first()
                if not prod:
                    continue
                exists = OrderItem.query.filter_by(
                    product_id=prod.id,
                    quantity=item.get("quantity", 1),
                    price=item.get("price", 0),
                    size=item.get("size"),
                    color=item.get("color"),
                    popularity=item.get("popularity"),
                    stock=item.get("stock"),
                ).first()
                if exists:
                    continue  # Đã có order_item này
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
            print("⚠️ Không có đơn hàng mới để thêm.")
