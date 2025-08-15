# service/faceBookApi.py
import logging
import os
import random
import time
from datetime import datetime, timedelta
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import func, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import load_only

from database_init import db
from models.deployed_app import DeployedApp
from models.facebook_api_status import FacebookApiStatus
from models.facebook_api_log import FacebookApiLog
from models.facebook_api_type import FacebookApiType

logger = logging.getLogger("deploy_logger")
logger.setLevel(logging.INFO)

GRAPH_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

IDLE_IF_NO_JOB_SECONDS = 30
MAX_SLEEP_UNTIL_NEXT_JOB = 60
CLAIM_JITTER_MIN = 2
CLAIM_JITTER_MAX = 5

DEFAULT_MAX_WORKERS = max(2, (os.cpu_count() or 1) * 2)
MAX_WORKERS = int(os.getenv("FACEBOOK_API_MAX_WORKERS", DEFAULT_MAX_WORKERS))
BATCH_LIMIT = int(
    os.getenv("FACEBOOK_API_BATCH_LIMIT", MAX_WORKERS * 20)
)

_http = requests.Session()
_http.mount(
    "https://",
    requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=3),
)

RATE_LIMIT_RULES = {429: 3600, 4: 900, 17: 1800, 80004: 1800}
SPECIAL_RATE_LIMIT_RULES = {(80004, 2446079): 1800}

# Health flag
_LAST_CLAIMED = 0


# ---------------- Helpers ----------------
def _cooldown_seconds(
    code: int | None, subcode: int | None, http_status: int | None
) -> int:
    if (
        code is not None
        and subcode is not None
        and (code, subcode) in SPECIAL_RATE_LIMIT_RULES
    ):
        return SPECIAL_RATE_LIMIT_RULES[(code, subcode)]
    if code is not None and code in RATE_LIMIT_RULES:
        return RATE_LIMIT_RULES[code]
    if http_status == 429:
        return RATE_LIMIT_RULES[429]
    return 300


def _normalize_numbers(st: FacebookApiStatus) -> None:
    st.total_calls = st.total_calls or 0
    st.total_success_calls = st.total_success_calls or 0
    st.total_errors = st.total_errors or 0
    st.daily_calls = st.daily_calls or 0
    st.daily_success_calls = st.daily_success_calls or 0
    st.reduced_days_count = st.reduced_days_count or 0


def _commit_with_retry(ctx: str, retries: int = 3, base_delay: float = 0.05) -> None:
    """Commit có retry, rollback ngay nếu gặp lock để tránh giữ metadata lock lâu."""
    for i in range(retries):
        try:
            db.session.commit()
            return
        except OperationalError as e:
            msg = str(getattr(e, "orig", e))
            if "1213" in msg or "1205" in msg:  # deadlock / lock wait timeout
                logger.warning(f"[DB-RETRY:{ctx}] Deadlock/Timeout, retry {i+1}")
                db.session.rollback()
                time.sleep(base_delay * (2**i) + random.random() * base_delay)
                continue
            db.session.rollback()
            logger.error(f"[DB-COMMIT-ERROR:{ctx}] {e}")
            raise
    db.session.commit()


def _json_error_fields(resp):
    try:
        data = resp.json()
    except Exception:
        return {}, None, None
    err = data.get("error", {})
    return data, err.get("code"), err.get("error_subcode")


def _pick_random_id(url: str, token: str, id_keys=("id", "account_id")):
    """GET url (must return {data: [...]}) and pick a random id by keys."""
    r = _http.get(url, params={"access_token": token}, timeout=10)
    if not r.ok:
        _, code, subcode = _json_error_fields(r)
        return None, (r.status_code, code, subcode, r.text, f"{url}[lookup]")
    try:
        items = r.json().get("data", [])
    except Exception:
        items = []
    if not items:
        return None, (r.status_code, None, None, r.text, f"{url}[no-data]")
    item = random.choice(items)
    for k in id_keys:
        if item.get(k):
            return item.get(k), None
    return None, (r.status_code, None, None, r.text, f"{url}[invalid-item]")


# ------------- Execute by api_type -------------
def _exec_type_call(api_type_name: str, token: str):
    if api_type_name == "ads_insights":
        acc_id, err = _pick_random_id(
            f"{BASE}/me/adaccounts", token, ("id", "account_id")
        )
        if err:
            http, code, subcode, txt, mark = err
            return (
                False,
                http,
                code,
                subcode,
                txt,
                f"type:ads_insights{mark.replace(BASE, '')}",
            )
        endpoint = f"/act_{acc_id}/insights"
        r = _http.get(f"{BASE}{endpoint}", params={"access_token": token}, timeout=10)
        if not r.ok:
            _, code, subcode = _json_error_fields(r)
            return False, r.status_code, code, subcode, r.text, endpoint
        return True, r.status_code, None, None, r.text, endpoint

    if api_type_name == "list_page_posts":
        page_id, err = _pick_random_id(f"{BASE}/me/accounts", token, ("id",))
        if err:
            http, code, subcode, txt, mark = err
            return (
                False,
                http,
                code,
                subcode,
                txt,
                f"type:list_page_posts{mark.replace(BASE, '')}",
            )
        endpoint = f"/{page_id}/posts"
        params = {
            "fields": "id,message,created_time,reactions.summary(true),comments.summary(true)",
            "access_token": token,
        }
        r = _http.get(f"{BASE}{endpoint}", params=params, timeout=10)
        if not r.ok:
            _, code, subcode = _json_error_fields(r)
            return False, r.status_code, code, subcode, r.text, endpoint
        return True, r.status_code, None, None, r.text, endpoint

    return (
        False,
        None,
        None,
        None,
        "Unsupported api_type",
        f"type:{api_type_name}[unsupported]",
    )


# ---------------- Core call ----------------
def call_facebook_api(deployed_app_id: int, api_type_id: int, access_token: str):
    st = FacebookApiStatus.query.filter_by(
        deployed_app_id=deployed_app_id, api_type_id=api_type_id
    ).first()

    if not st:
        st = FacebookApiStatus(
            deployed_app_id=deployed_app_id,
            api_type_id=api_type_id,
            daily_reset_at=datetime.utcnow(),
        )
        db.session.add(st)
        _commit_with_retry("init-status")

    _normalize_numbers(st)

    if not st.can_call():
        _commit_with_retry("skip-can_call")
        return None

    api_type = FacebookApiType.query.get(api_type_id)
    api_type_name = api_type.name if api_type else f"unknown:{api_type_id}"

    try:
        ok, http_status, code, subcode, resp_text, endpoint_str = _exec_type_call(
            api_type_name, access_token
        )

        if ok:
            st.record_call(success=True)
            _commit_with_retry("ok")
            return True

        if code is not None or http_status == 429:
            st.set_cooldown(
                _cooldown_seconds(code, subcode, http_status),
                error_code=code,
                error_subcode=subcode,
            )
        st.record_call(success=False)

        db.session.add(
            FacebookApiLog(
                deployed_app_id=deployed_app_id,
                api_endpoint=endpoint_str,
                status_code=http_status,
                error_code=code,
                error_subcode=subcode,
                message=resp_text,
            )
        )
        _commit_with_retry("fb-error")
        return None

    except requests.RequestException as e:
        st.set_cooldown(120, error_code=None, error_subcode=None)
        st.record_call(success=False)
        db.session.add(
            FacebookApiLog(
                deployed_app_id=deployed_app_id,
                api_endpoint=f"type:{api_type_name}[http-exception]",
                message=str(e),
            )
        )
        _commit_with_retry("http-exc")
        return None


# ---------------- Scheduler ----------------
def _run_call(app, app_id: int, api_type_id: int, token: str) -> None:
    with app.app_context():
        try:
            call_facebook_api(app_id, api_type_id, token)
        finally:
            db.session.remove()


def _has_any_status_rows() -> bool:
    return (
        db.session.query(FacebookApiStatus.deployed_app_id).limit(1).first() is not None
    )


def _claim_due_jobs(now: datetime, limit: int):
    """
    Claim theo 2 pha để tránh OR/COALESCE gây full-scan và next-key lock rộng.
    Pha 1: next_eligible_at <= now
    Pha 2: next_eligible_at IS NULL
    """
    claimed = []

    # Pha 1: record đã có lịch và đến hạn
    due1 = (
        FacebookApiStatus.query.filter(
            FacebookApiStatus.mode != "stopped",
            FacebookApiStatus.next_eligible_at <= now,
        )
        .order_by(FacebookApiStatus.next_eligible_at.asc())
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )

    for st in due1:
        st.next_eligible_at = now + timedelta(
            seconds=random.randint(CLAIM_JITTER_MIN, CLAIM_JITTER_MAX)
        )
        claimed.append((st.deployed_app_id, st.api_type_id))

    left = max(0, limit - len(due1))
    if left:
        # Pha 2: record chưa được lập lịch (NULL)
        due2 = (
            FacebookApiStatus.query.filter(
                FacebookApiStatus.mode != "stopped",
                FacebookApiStatus.next_eligible_at == None,
            )
            .with_for_update(skip_locked=True)
            .limit(left)
            .all()
        )
        for st in due2:
            st.next_eligible_at = now + timedelta(
                seconds=random.randint(CLAIM_JITTER_MIN, CLAIM_JITTER_MAX)
            )
            claimed.append((st.deployed_app_id, st.api_type_id))

    if claimed:
        _commit_with_retry("claim")

    return claimed


def due_scheduler_worker(app):
    global _LAST_CLAIMED
    with app.app_context():
        logger.info("[FB-DUE] Worker thread started.")
        # Giảm phạm vi lock + timeout ngắn cho worker
        try:
            db.session.execute(
                text("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            )
            db.session.execute(text("SET SESSION innodb_lock_wait_timeout = 3"))
            db.session.commit()
            logger.info("[FB-DUE] Session=READ COMMITTED, lock_wait_timeout=3s")
        except Exception:
            db.session.rollback()

        idle_ticks = 0

        while True:
            try:
                now = datetime.utcnow()

                if not _has_any_status_rows():
                    if idle_ticks % 20 == 0:
                        logger.info("[FB-DUE] No status rows yet, idle...")
                    idle_ticks += 1
                    time.sleep(IDLE_IF_NO_JOB_SECONDS)
                    continue

                claimed = _claim_due_jobs(now, BATCH_LIMIT)
                _LAST_CLAIMED = len(claimed)

                if not claimed:
                    if idle_ticks % 10 == 0:
                        nxt = (
                            db.session.query(
                                func.min(FacebookApiStatus.next_eligible_at)
                            )
                            .filter(FacebookApiStatus.next_eligible_at != None)
                            .scalar()
                        )
                        logger.info("[FB-DUE] No due jobs. next_min=%s", nxt)
                    idle_ticks += 1

                    next_time = (
                        db.session.query(func.min(FacebookApiStatus.next_eligible_at))
                        .filter(FacebookApiStatus.next_eligible_at != None)
                        .scalar()
                    )
                    if next_time:
                        sleep_s = max(
                            1, (next_time - datetime.utcnow()).total_seconds()
                        )
                        time.sleep(min(sleep_s, MAX_SLEEP_UNTIL_NEXT_JOB))
                    else:
                        time.sleep(IDLE_IF_NO_JOB_SECONDS)
                    continue

                idle_ticks = 0
                logger.info(
                    "[FB-DUE] Claimed %d jobs (ex: %s)...",
                    len(claimed),
                    claimed[:3],
                )

                # Map token cho các app được claim
                app_ids = {app_id for app_id, _ in claimed}
                tokens = {}
                if app_ids:
                    tokens = {
                        row.id: row.long_lived_user_token
                        for row in DeployedApp.query.options(
                            load_only(
                                DeployedApp.id, DeployedApp.long_lived_user_token
                            )
                        )
                        .filter(
                            DeployedApp.id.in_(app_ids),
                            DeployedApp.long_lived_user_token.isnot(None),
                        )
                        .all()
                    }

                # Gọi API cho từng job song song
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = []
                    for app_id, api_type_id in claimed:
                        token = tokens.get(app_id)
                        if not token:
                            st = FacebookApiStatus.query.filter_by(
                                deployed_app_id=app_id, api_type_id=api_type_id
                            ).first()
                            if st:
                                st.set_cooldown(300)
                                st.record_call(success=False)
                                _commit_with_retry("no-token")
                            continue
                        futures.append(
                            executor.submit(_run_call, app, app_id, api_type_id, token)
                        )
                    for f in futures:
                        f.result()

            except OperationalError as e:
                logger.error("[FB-DUE] DB error: %s", e)
                db.session.rollback()
                time.sleep(5)
            except Exception as e:
                logger.exception("[FB-DUE] Unexpected error: %s", e)
                time.sleep(5)


def start_background_task(app):
    """Start worker 1 lần duy nhất trong process chính của reloader."""
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        logger.info("[FB-DUE] Skip start (not main reloader process).")
        return

    for t in threading.enumerate():
        if t.name == "FB-DUE":
            logger.info("[FB-DUE] Already running, skip.")
            return

    logger.info("[FB-DUE] Starting background worker...")
    threading.Thread(
        target=due_scheduler_worker, args=(app,), daemon=True, name="FB-DUE"
    ).start()


# Tùy chọn: healthcheck nhanh
def fb_due_health():
    alive = any(t.name == "FB-DUE" and t.is_alive() for t in threading.enumerate())
    return {"alive": alive, "last_claimed": _LAST_CLAIMED}
