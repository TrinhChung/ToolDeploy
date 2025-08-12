# seed.py
from app import create_app
from database_init import db
from seeder.seed_user import seed_admin_user
from seeder.seed_cloudflare_account import seed_cloudflare_account
from seeder.seed_template import seed_template
from seeder.seed_company import seed_companies
from seeder.seed_product import seed_product
from seeder.seed_user_fe import seed_user_fe
from seeder.seed_order import seed_orders
from service.faceBookApi import start_background_task

app = create_app()
with app.app_context():
    db.create_all()
    seed_admin_user(app)
    seed_cloudflare_account(app)
    seed_template(app)
    seed_companies(app)
    seed_product(app)
    seed_user_fe(app)
    seed_orders(app)
    # Nếu muốn chỉ chạy 1 lần, đừng gọi trong Gunicorn worker
    # start_background_task()  # nếu cần, chuyển nó sang nơi khác
