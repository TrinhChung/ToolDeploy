import requests
import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database_init import db

logger = logging.getLogger("deploy_logger")


def process_expires_at(token_data):
    """Xử lý expires_at từ dữ liệu token của Facebook."""
    expires_at = token_data.get("expires_at")
    access_expires_at = token_data.get("data_access_expires_at")
    if expires_at is None and access_expires_at is None:
        raise RuntimeError("Lỗi xảy ra khi kiểm tra thời gian hết hạn.")
    if expires_at == 0 and access_expires_at == 0:
        return datetime(2100, 1, 1)
    if expires_at == 0:
        return datetime.fromtimestamp(access_expires_at)
    if access_expires_at == 0:
        return datetime.fromtimestamp(expires_at)
    return datetime.fromtimestamp(min(expires_at, access_expires_at))


def checkValidToken(userToken: str, appId: str, appSecret: str):
    """Kiểm tra token Facebook hợp lệ."""
    appAccessToken = f"{appId}|{appSecret}"
    checkUrl = f"https://graph.facebook.com/debug_token?input_token={userToken}&access_token={appAccessToken}"
    try:
        response = requests.get(checkUrl, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error(f"Lỗi kết nối khi kiểm tra token: {e}")
        return False, None

    if "data" in data:
        token_data = data["data"]
        return token_data.get("is_valid", False), process_expires_at(token_data)
    else:
        logger.warning(f"Không thể lấy thông tin token: {data}")
        return False, None


def genTokenForApp(shortLivedToken: str, appId: str, appSecret: str) -> str:
    """Đổi short-lived token sang long-lived token và cập nhật DB."""
    try:
        from util.facebook import checkValidToken  # tránh circular import

        is_valid, expireAt = checkValidToken(shortLivedToken, appId, appSecret)
        if not is_valid:
            raise RuntimeError(
                f"Token ngắn hạn {shortLivedToken} của app {appId} không hợp lệ."
            )

        logger.info("Đang đổi sang User Token dài hạn...")
        exchange_url = (
            f"https://graph.facebook.com/v21.0/oauth/access_token"
            f"?grant_type=fb_exchange_token"
            f"&client_id={appId}"
            f"&client_secret={appSecret}"
            f"&fb_exchange_token={shortLivedToken}"
        )

        resp = requests.get(exchange_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        LONG_LIVED_USER_TOKEN = data.get("access_token")
        if not LONG_LIVED_USER_TOKEN:
            raise RuntimeError("Không lấy được long-lived user token.")

        logger.info(f"User Token dài hạn: {LONG_LIVED_USER_TOKEN}")

        sql = """
        UPDATE deployed_app DA
        SET DA.long_lived_user_token = :token,
            DA.token_expired_at = :expire_at
        WHERE DA.env LIKE :pattern;
        """
        params = {
            "token": LONG_LIVED_USER_TOKEN,
            "expire_at": expireAt,
            "pattern": f"%{appId}%",
        }

        try:
            db.session.execute(text(sql), params)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Lỗi khi cập nhật token vào MySQL: {e}")
            return None

        return LONG_LIVED_USER_TOKEN

    except Exception as e:
        logger.error(f"Lỗi khi gen token: {e}")
        return None
