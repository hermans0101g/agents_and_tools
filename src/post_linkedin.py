# preview_from_asset_dsc.py

import json, threading, webbrowser, requests, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ---------- CONFIG ----------
CLIENT_ID = "78t0rea15rmplv"
CLIENT_SECRET = "WPL_AP1.csr2KEfrWpoLQ9H9.H5mzsA=="
REDIRECT_URI = "http://localhost:8000"   # must match your LinkedIn app exactly
ACCOUNT_ID  = "urn:li:sponsoredAccount:515449142"
ORG_URN     = "urn:li:organization:YOUR_ORG_ID"  # <-- put your org/company page URN here

LINKEDIN_VERSION = "202507"  # yyyymm
COMMON_HEADERS = {
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": LINKEDIN_VERSION,
}
TIMEOUT = 30
# ----------------------------

def bearer(token: str) -> dict:
    return {**COMMON_HEADERS, "Authorization": f"Bearer {token}"}

# --- Minimal localhost receiver for OAuth code (no copy/paste) ---
class OAuthHandler(BaseHTTPRequestHandler):
    code = None
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        OAuthHandler.code = (qs.get("code") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>LinkedIn auth complete</h1><p>You can close this tab.</p>")

def get_auth_code_via_localhost() -> str:
    server = HTTPServer(("localhost", 8000), OAuthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        "&scope=r_ads%20rw_ads"
    )
    print("Opening browser for LinkedIn auth...")
    webbrowser.open(auth_url, new=1, autoraise=True)

    # wait for the handler to receive the code
    while OAuthHandler.code is None:
        pass
    server.shutdown()
    return OAuthHandler.code

def exchange_code_for_token(auth_code: str) -> str:
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = requests.post(token_url, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["access_token"]

# --- Posts API (Direct Sponsored Content / dark post) ---
def create_dsc_post(access_token: str, org_urn: str, asset_urn: str) -> str:
    """
    Creates a 'dark' post (DSC) that can be used in ads without appearing on the feed.
    Returns the new post URN, e.g., 'urn:li:post:123...'
    """
    url = "https://api.linkedin.com/rest/posts"
    headers = {**bearer(access_token), "Content-Type": "application/json"}
    payload = {
        "author": org_urn,
        "commentary": "Let us craft your diversification strategy.",
        "visibility": "PUBLIC",
        "distribution": { "feedDistribution": "NONE" },  # NONE => dark (not published to followers)
        "content": { "media": { "id": asset_urn } },      # reference your uploaded image
        "adContext": { "dscStatus": "ACTIVE" },          # mark as Direct Sponsored Content
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }
    r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    if not r.ok:
        raise RuntimeError(f"Posts API failed: {r.status_code} {r.text}")
    data = r.json()
    return data["id"]  # e.g., urn:li:post:XXXX

def create_image_creative(access_token: str, account_urn: str, post_urn: str) -> str:
    """
    Build an IMAGE creative that references the DSC post.
    Returns the creative URN/id.
    """
    url = "https://api.linkedin.com/v2/adCreativesV2"
    headers = {**bearer(access_token), "Content-Type": "application/json"}
    payload = {
        "account": account_urn,
        "type": "IMAGE",
        "reference": post_urn
    }
    r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    if not r.ok:
        raise RuntimeError(f"Create creative failed: {r.status_code} {r.text}")
    data = r.json()
    return data.get("urn") or data.get("id")

def get_preview(access_token: str, account_urn: str, creative_urn: str) -> dict:
    url = "https://api.linkedin.com/v2/adPreviews"
    r = requests.get(url, headers=bearer(access_token),
                     params={"account": account_urn, "creative": creative_urn},
                     timeout=TIMEOUT)
    if not r.ok:
        raise RuntimeError(f"Preview failed: {r.status_code} {r.text}")
    return r.json()

def open_preview_in_browser(preview_json: dict):
    # LinkedIn may return an iframe HTML or a previewUrl; handle both
    import re
    if "previews" in preview_json and isinstance(preview_json["previews"], list):
        for item in preview_json["previews"]:
            url = item.get("previewUrl")
            if url:
                print("Opening preview:", url)
                webbrowser.open(url, new=1, autoraise=True)
                return
            iframe = item.get("previewIframe")
            if iframe:
                m = re.search(r'src="([^"]+)"', iframe)
                if m:
                    print("Opening preview iFrame src:", m.group(1))
                    webbrowser.open(m.group(1), new=1, autoraise=True)
                    return
    print("Preview JSON did not include a direct URL. Printing full JSON:")
    print(json.dumps(preview_json, indent=2))

def main():
    # 0) Read the asset URN saved by your upload script
    asset_urn = Path(__file__).with_name("last_asset_urn.txt").read_text(encoding="utf-8").strip()
    print("Using asset:", asset_urn)

    # 1) OAuth without manual paste
    code = get_auth_code_via_localhost()
    access_token = exchange_code_for_token(code)
    print("Access token acquired.")

    # 2) Create a Direct Sponsored Content (dark) post from the asset
    post_urn = create_dsc_post(access_token, ORG_URN, asset_urn)
    print("DSC post created:", post_urn)

    # 3) Create an IMAGE creative that references the post
    creative_urn = create_image_creative(access_token, ACCOUNT_ID, post_urn)
    print("Creative created:", creative_urn)

    # 4) Request a preview and open it
    preview = get_preview(access_token, ACCOUNT_ID, creative_urn)
    print("Preview payload:\n", json.dumps(preview, indent=2))
    open_preview_in_browser(preview)

if __name__ == "__main__":
    main()
