import requests
from database_init import db
from models.domain import Domain
from models.dns_record import DNSRecord
from models.cloudflare_acc import CloudflareAccount
from flask_login import current_user
from util.constant import DEPLOYED_APP_STATUS
# ========== GUARD & UTILS ==========

def _admin_guard():
    if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
        raise PermissionError("Bạn không có quyền thực hiện thao tác này!")

def build_cf_headers(cf_account):
    """Sinh headers cho Cloudflare API của 1 tài khoản."""
    return {
        "Authorization": f"Bearer {cf_account.api_token}",
        "Content-Type": "application/json"
    }

def get_cf_account_by_id(account_id):
    acc = CloudflareAccount.query.get(account_id)
    if not acc:
        raise Exception("Cloudflare Account không tồn tại!")
    return acc

# ========== DOMAIN (ZONE) ==========

def sync_domains_from_cf_with_account(cf_account):
    """
    Đồng bộ domain từ Cloudflare về DB (theo 1 tài khoản Cloudflare).
    Gán cloudflare_account_id cho domain, đồng bộ luôn DNS record từng domain.
    """
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)

    resp = requests.get(f"{BASE_URL}/zones", headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch domains: {resp.text}")

    domains_data = resp.json().get("result", [])
    for domain in domains_data:
        domain_name = domain["name"].strip().lower()
        zone_id = domain["id"]
        status = domain.get("status", DEPLOYED_APP_STATUS.pending.value)
        existing_domain = Domain.query.filter_by(name=domain_name).first()
        if existing_domain:
            existing_domain.zone_id = zone_id
            existing_domain.status = status
            existing_domain.cloudflare_account_id = cf_account.id
            db.session.commit()
            sync_dns_records_for_domain(existing_domain, cf_account)
        else:
            new_domain = Domain(
                name=domain_name,
                zone_id=zone_id,
                status=status,
                cloudflare_account_id=cf_account.id
            )
            db.session.add(new_domain)
            db.session.commit()
            sync_dns_records_for_domain(new_domain, cf_account)
    return domains_data

def create_cloudflare_zone(domain_name, cf_account):
    """Tạo zone mới trên Cloudflare (multi-account, truyền cf_account)."""
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    payload = {
        "name": domain_name,
        "account": {"id": cf_account.account_id},
        "jump_start": True,
    }
    resp = requests.post(f"{BASE_URL}/zones", headers=headers, json=payload)
    return resp.json()

def get_cloudflare_nameservers(zone_id, cf_account):
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    resp = requests.get(f"{BASE_URL}/zones/{zone_id}", headers=headers)
    data = resp.json()
    if data.get("success"):
        return data["result"]["name_servers"]
    return None

# ========== DNS RECORD ==========

def sync_dns_records_for_domain(domain_obj, cf_account):
    """
    Đồng bộ toàn bộ DNS record cho 1 domain về DB, ghi đè toàn bộ bản ghi cũ.
    """
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    resp = requests.get(f"{BASE_URL}/zones/{domain_obj.zone_id}/dns_records", headers=headers)
    if resp.status_code != 200:
        return
    records_data = resp.json().get("result", [])
    DNSRecord.query.filter_by(domain_id=domain_obj.id).delete()
    db.session.commit()
    for record in records_data:
        db.session.add(DNSRecord(
            domain_id=domain_obj.id,
            record_id=record.get("id"),
            record_type=record.get("type"),
            name=record.get("name"),
            content=record.get("content"),
            ttl=record.get("ttl"),
            proxied=record.get("proxied", False),
        ))
    db.session.commit()

def get_dns_records(zone_id, cf_account):
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    resp = requests.get(f"{BASE_URL}/zones/{zone_id}/dns_records", headers=headers)
    response_data = resp.json()
    if resp.status_code != 200 or not response_data.get("success", False):
        return {
            "success": False,
            "error": f"Failed to fetch DNS records: {response_data.get('errors', 'Unknown error')}",
        }
    records_data = response_data.get("result", [])
    domain = Domain.query.filter_by(zone_id=zone_id).first()
    if not domain:
        return {
            "success": False,
            "error": f"Domain với zone_id {zone_id} không tồn tại trong DB.",
        }
    DNSRecord.query.filter_by(domain_id=domain.id).delete()
    db.session.commit()
    for record in records_data:
        db.session.add(DNSRecord(
            domain_id=domain.id,
            record_id=record.get("id"),
            record_type=record.get("type"),
            name=record.get("name"),
            content=record.get("content"),
            ttl=record.get("ttl"),
            proxied=record.get("proxied"),
        ))
    db.session.commit()
    return {"success": True, "data": records_data}

def add_dns_record(zone_id, record_name, record_content, record_type="A", ttl=3600, proxied=False, cf_account=None):
    """Thêm bản ghi DNS vào Cloudflare (admin only, multi-account)."""
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    url = f"{BASE_URL}/zones/{zone_id}/dns_records"
    payload = {
        "type": record_type,
        "name": record_name,
        "content": record_content,
        "ttl": ttl,
        "proxied": proxied,
    }
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        error_message = resp.json().get("errors", "Unknown error")
        raise Exception(f"Failed to add DNS record: {error_message}")

def delete_dns_record_cf(zone_id, record_id, cf_account):
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    url = f"{BASE_URL}/zones/{zone_id}/dns_records/{record_id}"
    resp = requests.delete(url, headers=headers)
    if resp.status_code != 200:
        raise Exception("Failed to delete DNS record: " + str(resp.text))
    return resp.json()

def check_dns_record_exists(zone_id, subdns, cf_account):
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    resp = requests.get(f"{BASE_URL}/zones/{zone_id}/dns_records", headers=headers)
    if resp.status_code == 200:
        records_data = resp.json().get("result", [])
        for record in records_data:
            if record["name"] == subdns:
                return True
        return False
    else:
        raise Exception("Failed to fetch DNS records:", resp.text)


def add_or_update_txt_record(
    zone_id, subdns, dns, new_txt, ttl=3600, cf_account=None
):
    """
    Thêm hoặc cập nhật bản ghi TXT trên Cloudflare (multi-account).
    - Nếu chưa có bản ghi TXT thì thêm mới.
    - Nếu đã có nhưng khác nội dung thì cập nhật.
    - Nếu đã đúng nội dung thì không làm gì.
    """
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    record_name = f"{subdns}.{dns}" if subdns else dns
    url = f"{BASE_URL}/zones/{zone_id}/dns_records?type=TXT&name={record_name}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception("Failed to fetch DNS records:", resp.text)
    records = resp.json().get("result", [])

    if not records:
        # Không tồn tại, thêm mới
        return add_dns_record(
            zone_id,
            record_name,
            new_txt,
            record_type="TXT",
            ttl=ttl,
            proxied=False,
            cf_account=cf_account,
        )
    else:
        # Đã có record, kiểm tra content
        record = records[0]
        record_id = record["id"]
        current_content = record["content"]
        if current_content == new_txt:
            return {"success": True, "message": "TXT record đã tồn tại đúng nội dung."}
        # Cần update
        update_url = f"{BASE_URL}/zones/{zone_id}/dns_records/{record_id}"
        payload = {
            "type": "TXT",
            "name": record_name,
            "content": new_txt,
            "ttl": ttl,
            "proxied": False,
        }
        update_response = requests.put(update_url, json=payload, headers=headers)
        if update_response.status_code == 200:
            return update_response.json()
        else:
            error_message = update_response.json().get("errors", "Unknown error")
            raise Exception(f"Failed to update TXT record: {error_message}")


def update_dns_record(
    zone_id,
    record_id,
    record_name,
    record_content,
    record_type="A",
    ttl=3600,
    proxied=False,
    cf_account=None,
):
    """
    Cập nhật 1 DNS record đã tồn tại trên Cloudflare.
    - record_id: ID của bản ghi DNS cần update (lấy qua API hoặc đã lưu trong DB)
    - Các tham số còn lại tương tự add_dns_record
    """
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    url = f"{BASE_URL}/zones/{zone_id}/dns_records/{record_id}"
    payload = {
        "type": record_type,
        "name": record_name,
        "content": record_content,
        "ttl": ttl,
        "proxied": proxied,
    }
    resp = requests.put(url, json=payload, headers=headers)
    if resp.status_code in [200, 201]:
        return resp.json()
    else:
        error_message = resp.json().get("errors", "Unknown error")
        raise Exception(f"Failed to update DNS record: {error_message}")


def get_record_id_by_name(zone_id, record_name, record_type="A", cf_account=None):
    """
    Lấy record_id của bản ghi DNS theo tên và type.
    """
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    params = {
        "type": record_type,
        "name": record_name,
    }
    resp = requests.get(
        f"{BASE_URL}/zones/{zone_id}/dns_records", headers=headers, params=params
    )
    if resp.status_code == 200:
        records = resp.json().get("result", [])
        if records:
            return records[0]["id"]
        else:
            return None
    else:
        raise Exception(f"Failed to fetch DNS records: {resp.text}")


def delete_dns_record(zone_id, record_id, cf_account):
    """
    Xóa DNS record khỏi Cloudflare theo record_id (multi-account).
    """
    BASE_URL = "https://api.cloudflare.com/client/v4"
    headers = build_cf_headers(cf_account)
    url = f"{BASE_URL}/zones/{zone_id}/dns_records/{record_id}"
    resp = requests.delete(url, headers=headers)
    if resp.status_code == 200:
        return {"success": True, "message": "Đã xóa DNS record thành công."}
    else:
        error_message = resp.json().get("errors", resp.text)
        return {
            "success": False,
            "error": f"Failed to delete DNS record: {error_message}",
        }
