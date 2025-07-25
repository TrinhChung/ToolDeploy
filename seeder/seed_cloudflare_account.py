# seeder/seed_cloudflare_account.py

import os
from dotenv import load_dotenv
from models.cloudflare_acc import CloudflareAccount
from database_init import db

load_dotenv()

def seed_cloudflare_account(app):
    with app.app_context():
        api_token = os.getenv("CLOUD_FLARE_TOKEN")
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        name = "Account 1"
        email = "chungtrinh2k2@gmail.com"
        ns1 = "hank.ns.cloudflare.com"
        ns2 = "karsyn.ns.cloudflare.com"

        if not api_token or not account_id:
            print("❌ Thiếu CLOUD_FLARE_TOKEN hoặc CLOUDFLARE_ACCOUNT_ID trong .env")
            return

        # Kiểm tra tồn tại theo account_id (ưu tiên)
        cf_account = CloudflareAccount.query.filter_by(account_id=account_id).first()
        if not cf_account:
            cf_account = CloudflareAccount(
                name=name,
                email=email,
                api_token=api_token,
                account_id=account_id,
                ns1=ns1,
                ns2=ns2,
            )
            db.session.add(cf_account)
            db.session.commit()
            print(f"✅ Đã tạo CloudflareAccount: {name} ({account_id})")
        else:
            print("⚠️ CloudflareAccount đã tồn tại, bỏ qua.")
