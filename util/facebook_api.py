# util/facebook_api.py
import requests
from typing import Optional, Any, Dict

GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


class FacebookAPI:
    def __init__(self, access_token: str, timeout: int = 30):
        self.access_token = access_token
        self.timeout = timeout
        self._http = requests.Session()
        self._http.mount(
            "https://",
            requests.adapters.HTTPAdapter(
                pool_connections=20, pool_maxsize=20, max_retries=3
            ),
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{BASE_URL}{endpoint}"
        params = {**(params or {}), "access_token": self.access_token}
        resp = self._http.request(
            method,
            url,
            params=params,
            data=data,
            json=json,
            files=files,
            timeout=self.timeout,
        )
        if not resp.ok:
            raise Exception(f"Facebook API error {resp.status_code}: {resp.text}")
        return resp.json()

    def _get(self, endpoint: str, *, fields: Optional[str] = None, extra_params=None):
        params = {"fields": fields} if fields else {}
        if extra_params:
            params.update(extra_params)
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, *, data=None, json=None, files=None):
        return self._request("POST", endpoint, data=data, json=json, files=files)

    # ==== Campaigns ====
    def list_campaigns(self, ad_account_id: str):
        return self._get(
            f"/act_{ad_account_id}/campaigns",
            fields="id,name,status,objective,created_time",
        )

    def create_campaign(
        self,
        ad_account_id: str,
        name: str,
        objective: str,
        status: str,
        special_ad_categories: Optional[list] = None,
    ):
        return self._post(
            f"/act_{ad_account_id}/campaigns",
            data={
                "name": name,
                "objective": objective,
                "status": status,
                "special_ad_categories": special_ad_categories or [],
            },
        )

    # ==== Ads ====
    def list_ads(self, ad_account_id: str):
        return self._get(
            f"/act_{ad_account_id}/ads",
            fields=(
                "id,adset_id,name,status,"
                "insights{impressions,clicks,spend,cpm,cpc,cpp,ctr,frequency,date_start,date_stop}"
            ),
        )

    def get_adset(self, adset_id: str):
        return self._get(f"/{adset_id}", fields="id,name,status,daily_budget")

    def get_ad(self, ad_id: str):
        return self._get(
            f"/{ad_id}",
            fields="id,name,status,creative{object_type,object_story_spec,title,body}",
        )

    # ==== Insights ====
    def get_insights(self, ad_account_id: str):
        return self._get(
            f"/act_{ad_account_id}/insights", fields="impressions,clicks,spend"
        )

    # ==== Pages & Posts ====
    def list_pages(self):
        return self._get("/me/accounts")

    def list_page_posts(self, page_id: str):
        return self._get(
            f"/{page_id}/posts",
            fields="id,message,created_time,reactions.summary(true),comments.summary(true)",
        )

    def create_post(self, page_id: str, message: str):
        return self._post(f"/{page_id}/feed", data={"message": message})

    # ==== Video Upload ====
    def upload_video(self, page_id: str, video_path: str, description: str):
        with open(video_path, "rb") as f:
            return self._post(
                f"/{page_id}/videos",
                data={"description": description, "title": description},
                files={"file": f},
            )

    # ==== Reels Upload ====
    def start_reel_upload(self, page_id: str):
        return self._post(f"/{page_id}/video_reels", json={"upload_phase": "start"})

    def publish_reel(self, page_id: str, video_id: str, description: str):
        return self._post(
            f"/{page_id}/video_reels",
            json={
                "upload_phase": "finish",
                "video_state": "PUBLISHED",
                "video_id": video_id,
                "description": description,
            },
        )
