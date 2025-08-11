import requests
import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import random
from database_init import db
from models.deployed_app import DeployedApp
import os
import threading
import time

def process_expires_at(token_data):
    """
    Xử lý expires_at từ dữ liệu token của Facebook.
    Trả về thời gian hết hạn hoặc None nếu không có thời gian hết hạn.
    """
    expires_at = token_data.get("expires_at", None)
    access_expires_at = token_data.get("data_access_expires_at", None)
    if expires_at is None and access_expires_at is None:
        raise RuntimeError("Lỗi xảy ra khi kiểm tra thời gian hết hạn.")
    if expires_at == 0 and access_expires_at == 0:
        return datetime(
            2100, 1, 1
        )
    if expires_at == 0:
        return datetime.fromtimestamp(access_expires_at)
    if access_expires_at == 0:
        return datetime.fromtimestamp(expires_at)
    
    return datetime.fromtimestamp(min(expires_at, access_expires_at))

def checkValidToken(userToken:str, appId:str, appSecret:str):
    is_valid = False
    appAccessToken = f"{appId}|{appSecret}"
    checkUrl = f"https://graph.facebook.com/debug_token?input_token={userToken}&access_token={appAccessToken}"
    # Gửi yêu cầu
    response = requests.get(checkUrl, timeout=10)
    data = response.json()

    if "data" in data:
        token_data = data["data"]
        if token_data:
            is_valid = token_data.get("is_valid", False)
            expire_at = process_expires_at(token_data)
            return is_valid, expire_at
    else:
        print("Không thể lấy thông tin token.")
        print(data)
        raise RuntimeError(f"Lỗi xảy ra khi kiểm tra token: {userToken} với app: {appId}")
        
def genTokenForApp(shortLivedToken:str, appId:str, appSecret:str) -> str:
    is_valid = False
    expireAt = None
    try:
        is_valid, expireAt = checkValidToken(shortLivedToken, appId, appSecret)
        if is_valid:
            # =============================
            # 1. Đổi sang User Token dài hạn
            # =============================
            print("🔄 Đang đổi sang User Token dài hạn...")
            exchange_url = (
                f"https://graph.facebook.com/v21.0/oauth/access_token"
                f"?grant_type=fb_exchange_token"
                f"&client_id={appId}"
                f"&client_secret={appSecret}"
                f"&fb_exchange_token={shortLivedToken}"
            )

            resp = requests.get(exchange_url)
            resp.raise_for_status()
            data = resp.json()

            LONG_LIVED_USER_TOKEN = data.get("access_token")
            print("User Token dài hạn:", LONG_LIVED_USER_TOKEN)
            
            sql = f"""
            UPDATE DEPLOYED_APP DA
            SET DA.long_lived_user_token=:token, DA.token_expired_at=:expire_at 
            WHERE ENV LIKE=="%:app_id%";
            """

            params = {"token": LONG_LIVED_USER_TOKEN, "app_id": appId, "expire_at": expireAt}
            db.session.execute(text(sql), params)
            db.session.commit()

            return LONG_LIVED_USER_TOKEN

            # # =============================
            # # 2. Lấy Page Access Token
            # # =============================
            # print("Đang lấy Page Access Token...")
            # # APP_SCOPED_USER_ID: với user hiện tại, bạn có thể dùng "me"
            # page_url = f"https://graph.facebook.com/v12.0/me/accounts?access_token={LONG_LIVED_USER_TOKEN}"
            # print(f"call api: {page_url}")

            # resultList = []

            # resp = requests.get(page_url)
            # resp.raise_for_status()
            # pages = resp.json()

            # if "data" in pages and len(pages["data"]) != 0:
            #     for page in pages["data"]:
            #         page_name = page.get("name")
            #         page_id = page.get("id")
            #         page_token = page.get("access_token")

            #         # Tạo dict theo định dạng yêu cầu
            #         page_dict = {
            #             page_id: {
            #                 "name": page_name,
            #                 "pageToken": page_token
            #             }
            #         }
            #         resultList.append(page_dict)
            # else:
            #     print("Không tìm thấy page nào hoặc token không đủ quyền.")

            # # =============================
            # # 3. (Tùy chọn) Lưu token vào file
            # # =============================
            # with open("tokens.txt", "w", encoding="utf-8") as f:
            #     f.write(f"LONG_LIVED_USER_TOKEN={LONG_LIVED_USER_TOKEN}\n")
            #     if "data" in pages:
            #         for page in pages["data"]:
            #             f.write(f"PAGE_{page['id']}_TOKEN={page['access_token']}\n")

            # print("💾 Token đã lưu vào tokens.txt")
        else:
            raise RuntimeError(f"short token: {shortLivedToken} của app: {appId} không còn hiệu lực.")
    except requests.Timeout:
        print("Request timed out.")
        return None
    except requests.RequestException as e:
        print(f"Lỗi khi gen token: {str(e)}")
        return None
    except RuntimeError as e:
        print(f"Lỗi khi gen token: {str(e)}")
        return None
    except SQLAlchemyError as e:
        db.session.rollback()
        print("Error: Lỗi khi mysql update token", str(e))
        return None

def callApiFrequently():
    while True:
        try:
            apps = (
                DeployedApp.query
                .with_entities(DeployedApp.long_lived_user_token)
                .filter(DeployedApp.long_lived_user_token.isnot(None))
                .all()
            )

            length = len(apps)
            for i in range(length):
                token = apps[i][0]
                try:
                    accountListUrl = f"https://graph.facebook.com/v21.0/me/adaccounts"
                    params_account = {"access_token": token}
                    time.sleep(random.uniform(2, 5))
                    accountListResponse = requests.get(accountListUrl, params=params_account, timeout=10)
                    accountListResponse.raise_for_status()
                    accountList = accountListResponse.json()

                    if "data" in accountList and len(accountList["data"]) != 0:
                        for account in accountList["data"]:
                            try:
                                account_id = account.get("id") or account.get("account_id")
                                if not account_id:
                                    print("Không tìm thấy account_id:", account)
                                    continue

                                campaignListUrl = f"https://graph.facebook.com/v21.0/{account_id}/campaigns"
                                params_campaign = {
                                    "fields": "start_time,objective,name,status,created_time,stop_time,special_ad_categories",
                                    "access_token": token,
                                }
                                time.sleep(random.uniform(2, 5))
                                response = requests.get(campaignListUrl, params=params_campaign, timeout=10)
                                response.raise_for_status()
                                campaignList = response.json()

                                print(f"Campaigns for account {account_id}: {campaignList.get('data', [])}")

                            except requests.RequestException as e:
                                print(f"Lỗi khi lấy campaigns cho account {account_id}: {e}")
                            except Exception as e:
                                print(f"Lỗi không xác định khi xử lý campaigns: {e}")

                except requests.RequestException as e:
                    print(f"Lỗi khi lấy danh sách tài khoản quảng cáo với token: {e}")
                except Exception as e:
                    print(f"Lỗi không xác định khi xử lý token: {e}")

        except Exception as e:
            print(f"Lỗi khi xử lý callApiFrequently: {e}")

        print(f"Hoàn tất 1 vòng vào lúc {datetime.utcnow()}, nghỉ 30 - 60 phút...")
        time.sleep(random.uniform(1800, 3600))

def start_background_task():
    t = threading.Thread(target=callApiFrequently, daemon=True)
    t.start()