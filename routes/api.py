from flask import Blueprint, jsonify, request, abort
from datetime import datetime
from database_init import db
from models.product import Product
from models.user_fe import UserFE
from models.order import Order
from models.order_item import OrderItem
from models.company import Company
from models.website import Website
from urllib.parse import quote_plus

api_bp = Blueprint('api_fe', __name__, url_prefix='/api')


def _product_to_dict(product: Product) -> dict:
    """Chuyển đối tượng Product thành dict JSON."""
    return {
        "id": product.id,
        "title": product.title,
        "image": product.image,
        "category": product.category,
        "price": product.price,
        "popularity": product.popularity,
        "stock": product.stock,
    }


def _user_to_dict(user: UserFE) -> dict:
    """Định dạng đối tượng UserFE thành dict."""
    return {
        "id": user.id,
        "name": user.name,
        "lastname": user.lastname,
        "email": user.email,
        "password": user.password,
        "phone": user.phone,
        "address": user.address,
    }


def _order_to_dict(order: Order) -> dict:
    """Định dạng đối tượng Order cùng các item liên quan."""
    items = []
    for item in order.order_items:
        prod = item.product
        items.append({
            "id": f"{prod.id}{item.size}{item.color}",
            "image": prod.image,
            "title": prod.title,
            "category": prod.category,
            "price": item.price,
            "quantity": item.quantity,
            "size": item.size,
            "color": item.color,
            "popularity": prod.popularity,
            "stock": prod.stock,
        })
    return {
        "id": order.id,
        "data": {
            "emailAddress": order.user_fe.email,
            "firstName": order.user_fe.name,
            "lastName": order.user_fe.lastname,
            "address": order.shipping_address,
            "phone": order.phone,
            "paymentType": order.payment_type,
        },
        "products": items,
        "subtotal": order.subtotal,
        "user": {"email": order.user_fe.email, "id": order.user_fe.id},
        "orderStatus": order.order_status,
        "orderDate": order.order_date.isoformat() if order.order_date else None,
    }


@api_bp.route('/products')
def list_products():
    """Trả về danh sách sản phẩm."""
    products = Product.query.all()
    return jsonify([_product_to_dict(p) for p in products])


@api_bp.route('/products/<int:product_id>')
def get_product(product_id):
    """Lấy thông tin chi tiết một sản phẩm."""
    product = Product.query.get_or_404(product_id)
    return jsonify(_product_to_dict(product))


@api_bp.route('/users', methods=['GET', 'POST'])
def users():
    """Danh sách hoặc tạo mới người dùng FE."""
    if request.method == 'GET':
        users = UserFE.query.all()
        return jsonify([_user_to_dict(u) for u in users])

    data = request.get_json(silent=True) or {}
    user = UserFE(
        name=data.get('name'),
        lastname=data.get('lastname'),
        email=data.get('email'),
        password=data.get('password'),
        phone=data.get('phone'),
        address=data.get('address'),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(_user_to_dict(user)), 201


@api_bp.route('/users/<int:user_id>', methods=['GET', 'PUT'])
def user_detail(user_id):
    """Truy vấn hoặc cập nhật một người dùng FE."""
    user = UserFE.query.get_or_404(user_id)
    if request.method == 'GET':
        return jsonify(_user_to_dict(user))

    data = request.get_json(silent=True) or {}
    user.name = data.get('name', user.name)
    user.lastname = data.get('lastname', user.lastname)
    user.email = data.get('email', user.email)
    user.password = data.get('password', user.password)
    user.phone = data.get('phone', user.phone)
    user.address = data.get('address', user.address)
    db.session.commit()
    return jsonify(_user_to_dict(user))


@api_bp.route('/orders', methods=['GET', 'POST'])
def orders():
    """Danh sách hoặc tạo mới đơn hàng."""
    if request.method == 'GET':
        orders = Order.query.order_by(Order.id).all()
        return jsonify([_order_to_dict(o) for o in orders])

    data = request.get_json(silent=True) or {}
    user_info = data.get('user', {})
    user = None
    if 'id' in user_info:
        user = UserFE.query.get(user_info['id'])
    if not user and user_info.get('email'):
        user = UserFE.query.filter_by(email=user_info['email']).first()
    if not user:
        abort(400, description='User not found')

    order = Order(
        user_fe_id=user.id,
        order_status=data.get('orderStatus', 'Processing'),
        order_date=datetime.utcnow(),
        subtotal=data.get('subtotal', 0),
        shipping_address=data.get('data', {}).get('address'),
        phone=data.get('data', {}).get('phone'),
        payment_type=data.get('data', {}).get('paymentType'),
    )
    db.session.add(order)
    db.session.flush()

    for item in data.get('products', []):
        prod = Product.query.filter_by(title=item.get('title')).first()
        if not prod:
            continue
        order_item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            quantity=item.get('quantity', 1),
            price=item.get('price', prod.price),
            size=item.get('size'),
            color=item.get('color'),
            popularity=item.get('popularity'),
            stock=item.get('stock'),
        )
        db.session.add(order_item)
    db.session.commit()
    return jsonify(_order_to_dict(order)), 201


@api_bp.route('/orders/<int:order_id>')
def order_detail(order_id):
    """Lấy chi tiết một đơn hàng."""
    order = Order.query.get_or_404(order_id)
    return jsonify(_order_to_dict(order))


def normalize_google_map_embed(raw_map: str | None, address: str | None) -> str:
    """
    Trả về HTML <iframe> nhúng Google Maps từ:
    - iframe: rút src và đảm bảo có output=embed
    - URL:    đảm bảo có output=embed
    - địa chỉ/chuỗi thường: build URL q=...&output=embed
    - rỗng: nếu có address thì dùng address; nếu không -> ""
    """

    def _ensure_output_embed(u: str) -> str:
        if not u:
            return ""
        if "output=embed" in u:
            return u
        return u + ("&output=embed" if "?" in u else "?output=embed")

    def _extract_src(html: str) -> str:
        h = html
        low = h.lower()
        i = low.find("src=")
        if i == -1:
            return ""
        if i + 4 >= len(h):
            return ""
        q = h[i + 4]
        if q not in ('"', "'"):
            return ""
        j = h.find(q, i + 5)
        if j == -1:
            return ""
        return h[i + 5 : j]

    raw = (raw_map or "").strip()
    addr = (address or "").strip()
    src = ""

    if not raw:
        if addr:
            src = _ensure_output_embed(
                f"https://www.google.com/maps?q={quote_plus(addr)}"
            )
    else:
        low = raw.lower()
        if "<iframe" in low:
            src = _ensure_output_embed(_extract_src(raw))
        elif low.startswith("http"):
            src = _ensure_output_embed(raw)
        else:
            src = _ensure_output_embed(
                f"https://www.google.com/maps?q={quote_plus(raw)}"
            )

    if not src:
        return ""
    return (
        f'<iframe src="{src}" width="100%" height="300" style="border:0;" '
        f'allowfullscreen="" loading="lazy" '
        f'referrerpolicy="no-referrer-when-downgrade"></iframe>'
    )


@api_bp.route("/company", methods=["GET"])
def get_company_by_origin():
    """Trả về thông tin công ty dựa trên Origin domain (frontend)."""
    origin = request.headers.get("X-Client-Domain")
    print("Frontend Domain:", origin)
    domain_name = origin or None

    company = None

    if domain_name:
        # Tìm website theo static_page_link
        website = Website.query.filter_by(static_page_link=domain_name).first()
        if website:
            company = Company.query.get(website.company_id)

    if not company:
        company = Company.query.first()

    if not company:
        return jsonify({"error": "No company found"}), 404

    google_map_embed_norm = normalize_google_map_embed(
        company.google_map_embed, company.address
    )

    return jsonify(
        {
            "name": company.name,
            "name_vn": getattr(company, "name_vn", None),  # Tên tiếng Việt
            "short_name": getattr(company, "short_name", None),  # Tên viết tắt
            "address": company.address,
            "hotline": company.hotline,
            "email": company.email,
            "license_no": company.license_no,
            "organization_no": getattr(company, "organization_no", None),  # Mã tổ chức
            "approval_date": getattr(company, "approval_date", None),  # Ngày phê duyệt
            "expiry_date": getattr(company, "expiry_date", None),  # Ngày hết hạn
            "google_map_embed": google_map_embed_norm,
            "logo_url": company.logo_url,
            "footer_text": company.footer_text,
            "description": company.description,
            "note": company.note,
        }
    )
