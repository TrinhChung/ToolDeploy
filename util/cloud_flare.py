import os
import requests
from dotenv import load_dotenv
from database_init import db
from models.domain import Domain
from models.dns_record import DNSRecord
from util.until import extract_base_domain
from flask_login import current_user

load_dotenv()

API_TOKEN = os.getenv("CLOUD_FLARE_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
BASE_URL = "https://api.cloudflare.com/client/v4"
headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


# ========== ADMIN GUARD ==========
def _admin_guard():
    if not current_user.is_authenticated or not getattr(
        current_user, "is_admin", False
    ):
        raise PermissionError("Bạn không có quyền thực hiện thao tác này!")


# ========== DOMAIN ==========
def sync_domains_from_cf():
    """Đồng bộ domain từ Cloudflare về database (chỉ admin)."""
    _admin_guard()
    response = requests.get(f"{BASE_URL}/zones", headers=headers)
    if response.status_code == 200:
        domains_data = response.json().get("result", [])
        for domain in domains_data:
            existing_domain = Domain.query.filter_by(name=domain["name"]).first()
            if not existing_domain:
                new_domain = Domain(
                    name=domain["name"],
                    zone_id=domain["id"],
                    status=domain.get("status", "pending"),
                )
                db.session.add(new_domain)
            else:
                existing_domain.zone_id = domain["id"]
                existing_domain.status = domain.get("status", "pending")
        db.session.commit()
        return domains_data
    else:
        raise Exception("Failed to fetch domains:", response.text)


def create_cloudflare_zone(domain_name):
    """Tạo zone mới trên Cloudflare (admin only)."""
    _admin_guard()
    payload = {
        "name": domain_name,
        "account": {"id": CLOUDFLARE_ACCOUNT_ID},
        "jump_start": True,
    }
    response = requests.post(f"{BASE_URL}/zones", headers=headers, json=payload)
    return response.json()


def get_cloudflare_nameservers(zone_id):
    """Lấy nameserver của domain trong Cloudflare."""
    response = requests.get(f"{BASE_URL}/zones/{zone_id}", headers=headers)
    data = response.json()
    if data.get("success"):
        return data["result"]["name_servers"]
    return None


# ========== DNS RECORD ==========
def get_dns_records(zone_id):
    """Lấy danh sách DNS records từ Cloudflare và đồng bộ vào DB (admin only)."""
    _admin_guard()
    try:
        response = requests.get(
            f"{BASE_URL}/zones/{zone_id}/dns_records", headers=headers
        )
        response_data = response.json()
        if response.status_code != 200 or not response_data.get("success", False):
            return {
                "success": False,
                "error": f"Failed to fetch DNS records: {response_data.get('errors', 'Unknown error')}",
            }
        records_data = response_data.get("result", [])
        if not records_data:
            return {"success": False, "error": "No DNS records found for this zone."}
        first_record_name = records_data[0].get("name", None)
        if not first_record_name:
            return {
                "success": False,
                "error": "Invalid response: missing 'name' field.",
            }
        zone_name = extract_base_domain(first_record_name)
        domain = Domain.query.filter_by(name=zone_name).first()
        if not domain:
            return {
                "success": False,
                "error": f"Domain '{zone_name}' not found in database.",
            }
        # Cập nhật hoặc thêm DNS records
        for record in records_data:
            existing_record = DNSRecord.query.filter_by(
                domain_id=domain.id, name=record["name"], record_type=record["type"]
            ).first()
            if existing_record:
                existing_record.content = record["content"]
                existing_record.ttl = record["ttl"]
                existing_record.proxied = record["proxied"]
            else:
                new_record = DNSRecord(
                    domain_id=domain.id,
                    record_type=record["type"],
                    name=record["name"],
                    content=record["content"],
                    ttl=record["ttl"],
                    proxied=record["proxied"],
                )
                db.session.add(new_record)
        db.session.commit()
        return {"success": True, "data": records_data}
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error while fetching DNS records: {str(e)}",
        }
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def get_data_dns_records(zone_id):
    """Chỉ lấy dữ liệu DNS (read only, không cập nhật DB)."""
    response = requests.get(f"{BASE_URL}/zones/{zone_id}/dns_records", headers=headers)
    if response.status_code == 200:
        return response.json().get("result", [])
    else:
        raise Exception("Failed to fetch DNS records:", response.text)


def add_dns_record(
    zone_id, record_name, record_content, record_type="A", ttl=3600, proxied=False
):
    """Thêm bản ghi DNS vào Cloudflare (admin only)."""
    _admin_guard()
    url = f"{BASE_URL}/zones/{zone_id}/dns_records"
    payload = {
        "type": record_type,
        "name": record_name,
        "content": record_content,
        "ttl": ttl,
        "proxied": proxied,
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        error_message = response.json().get("errors", "Unknown error")
        raise Exception(f"Failed to add DNS record: {error_message}")


def check_dns_record_exists(zone_id, subdns):
    """Kiểm tra xem bản ghi DNS đã tồn tại hay chưa."""
    response = requests.get(f"{BASE_URL}/zones/{zone_id}/dns_records", headers=headers)
    if response.status_code == 200:
        records_data = response.json().get("result", [])
        for record in records_data:
            if record["name"] == subdns:
                return True
        return False
    else:
        raise Exception("Failed to fetch DNS records:", response.text)


def add_or_update_txt_record(zone_id, subdns, dns, old_txt, new_txt, ttl=2147483647):
    """Thêm hoặc cập nhật bản ghi TXT trên Cloudflare (admin only)."""
    _admin_guard()
    record_name = f"{subdns}.{dns}" if subdns else dns
    url = f"{BASE_URL}/zones/{zone_id}/dns_records?type=TXT&name={record_name}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to fetch DNS records:", response.text)
    records = response.json().get("result", [])
    if not records or not old_txt:
        return add_dns_record(
            zone_id, record_name, new_txt, record_type="TXT", ttl=ttl, proxied=False
        )
    else:
        record = records[0]
        record_id = record["id"]
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


def add_custom_domain_to_pages(project_name, custom_domain):
    """Gán domain vào Cloudflare Pages project (admin only)."""
    _admin_guard()
    url = f"{BASE_URL}/accounts/{CLOUDFLARE_ACCOUNT_ID}/pages/projects/{project_name}/domains"
    payload = {"name": custom_domain}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"Custom domain {custom_domain} added to project {project_name}.")


# ==== END ====
