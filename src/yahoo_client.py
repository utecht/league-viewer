import os, base64, time, requests
from typing import Dict, Any

TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API_ROOT = "https://fantasysports.yahooapis.com/fantasy/v2"


class YahooClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._token = None
        self._exp = 0

    def _ensure_token(self):
        if self._token and time.time() < self._exp - 30:
            return
        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
        r.raise_for_status()
        j = r.json()
        self._token = j["access_token"]
        self._exp = time.time() + int(j.get("expires_in", 3600))

    def get_json(self, path: str, params=None) -> Dict[str, Any]:
        self._ensure_token()
        headers = {"Authorization": f"Bearer {self._token}"}
        # Yahoo returns XML by default; ask for JSON
        p = {"format": "json"}
        if params:
            p.update(params)
        url = f"{API_ROOT}/{path}"
        r = requests.get(url, headers=headers, params=p, timeout=30)
        r.raise_for_status()
        return r.json()
