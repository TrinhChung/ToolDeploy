# Thiết kế cơ bản

Ứng dụng xây dựng trên Flask với kiến trúc module hóa. Mỗi nhóm chức năng được triển khai thành một *blueprint*. Các thành phần phụ trợ như đăng nhập, ORM, migrate được cấu hình trong `app.py`.

## Đăng ký blueprint

Trong `create_app()` của `app.py` các blueprint được import và đăng ký như sau:

```python
from routes.home import home_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.server import server_bp
from routes.domain import domain_bp
from routes.dns import dns_bp
from routes.deployed_app import deployed_app_bp
from routes.cloudflare_account import cloudflare_bp
from routes.company import company_bp
from routes.website import website_bp
from routes.api import api_bp

app.register_blueprint(home_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(server_bp)
app.register_blueprint(domain_bp)
app.register_blueprint(dns_bp)
app.register_blueprint(deployed_app_bp)
app.register_blueprint(cloudflare_bp)
app.register_blueprint(company_bp)
app.register_blueprint(website_bp)
app.register_blueprint(api_bp)
```

Flask‑Login được dùng để quản lý phiên đăng nhập. Các request trừ API đều yêu cầu đăng nhập, được kiểm soát thông qua `@app.before_request`.

Database sử dụng SQLAlchemy với MySQL (cấu hình trong biến môi trường). Migrate dùng `Flask-Migrate`.

Toàn bộ thao tác deploy ứng dụng được chạy ở background thread, đồng thời cập nhật trạng thái trong bảng `DeployedApp`.
