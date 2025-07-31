import logging
from flask import flash

# Import các hàm sử dụng cloudflare API của bạn
from util.cloud_flare import check_dns_record_exists, add_dns_record

logger = logging.getLogger("cloudflare_dns_helper")


def create_dns_record_if_needed(subdomain, domain, server, flash_msg=True):
    """
    Tạo bản ghi A trên Cloudflare nếu cần.
    domain: row domain (bắt buộc có .zone_id, .name, .cloudflare_account)
    server: row server (bắt buộc có .ip)
    subdomain: phần đầu (ví dụ "abc")
    flash_msg: show lỗi cho người dùng nếu có
    Return True nếu đã có hoặc tạo mới thành công, False nếu lỗi.
    """
    if not subdomain:  # Root domain thì bỏ qua
        return True
    cf_account = getattr(domain, "cloudflare_account", None)
    domain_name = getattr(domain, "name", "")
    record_name = f"{subdomain}.{domain_name}"
    try:
        exists = check_dns_record_exists(
            zone_id=domain.zone_id, subdns=record_name, cf_account=cf_account
        )
        if exists:
            logger.warning(f"⚠️ Bản ghi A {record_name} đã tồn tại.")
            if flash_msg:
                flash(f"⚠️ Bản ghi A {record_name} đã tồn tại.", "danger")
            return False
        add_dns_record(
            zone_id=domain.zone_id,
            record_name=record_name,
            record_content=server.ip,
            record_type="A",
            ttl=3600,
            proxied=False,
            cf_account=cf_account,
        )
        logger.info(f"✅ Đã tạo bản ghi A: {record_name} → {server.ip}")
        return True
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo bản ghi A: {str(e)}")
        if flash_msg:
            flash(f"Lỗi tạo bản ghi DNS: {e}", "danger")
        return False
