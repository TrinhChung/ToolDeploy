import time
import requests
from datetime import datetime
from database_init import db
from models.deployed_app import DeployedApp
from queue_config import queue

FB_API = "https://graph.facebook.com/v21.0"
DELAY_BETWEEN_CALLS = 0.05  # nghỉ giữa mỗi request
BATCH_SIZE = 10  # số call trong mỗi job con
TOTAL_PAGE_CALLS = 1500  # tổng call cho pages
TOTAL_ADS_CALLS = 1500  # tổng call cho ads


def process_app_api(app_id):
    """Job cha: chia nhỏ thành nhiều job con."""
    app = DeployedApp.query.get(app_id)
    if not app:
        return

    token = app.long_lived_user_token

    # --- Lấy pages ---
    pages = []
    res = requests.get(f"{FB_API}/me/accounts", params={"access_token": token})
    if res.ok:
        pages = res.json().get("data", [])
    else:
        _append_log(app, f"Lỗi lấy danh sách page: {res.text}")

    # --- Lấy ad accounts ---
    accounts = []
    res = requests.get(f"{FB_API}/me/adaccounts", params={"access_token": token})
    if res.ok:
        accounts = res.json().get("data", [])
    else:
        _append_log(app, f"Lỗi lấy danh sách ad account: {res.text}")

    # --- Chia job con cho Pages ---
    if pages:
        calls_per_page_total = max(1, TOTAL_PAGE_CALLS // len(pages))
        for page in pages:
            for start in range(0, calls_per_page_total, BATCH_SIZE):
                queue.enqueue(
                    fetch_page_posts,
                    app_id,
                    page["id"],
                    page["access_token"],
                    BATCH_SIZE,
                )

    # --- Chia job con cho Ads ---
    if accounts:
        calls_per_acc_total = max(1, TOTAL_ADS_CALLS // len(accounts))
        for acc in accounts:
            for start in range(0, calls_per_acc_total, BATCH_SIZE):
                queue.enqueue(
                    fetch_ads_details,
                    app_id,
                    acc["id"].replace("act_", ""),
                    token,
                    BATCH_SIZE,
                )

    _append_log(app, f"Đã enqueue các job con cho app #{app_id}")


def fetch_page_posts(app_id, page_id, page_token, batch_size):
    """Job con: lấy bài viết của 1 page."""
    app = DeployedApp.query.get(app_id)
    if not app:
        return

    log_lines = []
    for _ in range(batch_size):
        res = requests.get(
            f"{FB_API}/{page_id}/posts",
            params={
                "fields": "id,message,created_time,reactions.summary(true),comments.summary(true)",
                "access_token": page_token,
            },
        )

        if not res.ok:
            log_lines.append(f"Lỗi page {page_id}: {res.text}")
            if _is_rate_limit(res):
                break
        time.sleep(DELAY_BETWEEN_CALLS)

    _append_log(app, "\n".join(log_lines))


def fetch_ads_details(app_id, account_id, token, batch_size):
    """Job con: lấy chi tiết ads của 1 account."""
    app = DeployedApp.query.get(app_id)
    if not app:
        return

    log_lines = []
    for _ in range(batch_size):
        res = requests.get(
            f"{FB_API}/act_{account_id}/ads",
            params={
                "fields": (
                    "id,adset_id,name,status,"
                    "insights{impressions,clicks,spend,cpm,cpc,cpp,ctr,frequency,date_start,date_stop}"
                ),
                "access_token": token,
            },
        )

        if not res.ok:
            log_lines.append(f"Lỗi ads {account_id}: {res.text}")
            if _is_rate_limit(res):
                break
        time.sleep(DELAY_BETWEEN_CALLS)

    _append_log(app, "\n".join(log_lines))


def _is_rate_limit(res):
    """Kiểm tra rate limit từ Facebook API."""
    if res.status_code == 429:
        return True
    try:
        data = res.json()
        if data.get("error", {}).get("code") == 4:
            return True
    except Exception:
        pass
    return False


def _append_log(app, text):
    """Thêm log vào app.log và commit DB."""
    if not text:
        return
    if not app.log:
        app.log = ""
    app.log += f"\n{text}"
    app.updated_at = datetime.utcnow()
    db.session.commit()
