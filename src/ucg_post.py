# preview_from_asset.py
import os, json, requests
from pathlib import Path

# ---------- CONFIG ----------
CLIENT_ID = "78t0rea15rmplv"
CLIENT_SECRET = "WPL_AP1.csr2KEfrWpoLQ9H9.H5mzsA=="
REDIRECT_URI = "http://localhost:8000"  # must match LinkedIn app config
ACCOUNT_ID = "urn:li:sponsoredAccount:515449142"
ORG_URN    = "urn:li:organization:YOUR_ORG_ID"  # <-- your company page URN

LINKEDIN_VERSION = "202507"
COMMON_HEADERS = {
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": LINKEDIN_VERSION,
}
# ----------------------------

def bearer(token):
    return {**COMMON_HEADERS, "Authorization": f"Bearer {token}"}

def get_access_token():
    # Step 1: Direct user to LinkedIn authorization
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={requests.utils.quote(REDIRECT_URI, safe='')}"
        "&scope=r_ads%20rw_ads"
    )
    print("\n1) Open this URL in your browser and authorize:")
    print(auth_url)
    print()
    auth_code = input("Paste the 'code' from the redirect URL here: ").strip()

    # Step 2: Exchange auth code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    resp = requests.post(token_url, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]

def create_ugc_post(access_token, org_urn, asset_urn):
    url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": org_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": "Let us craft your diversification strategy."},
                "shareMediaCategory": "IMAGE",
                "media": [{
                    "status": "READY",
                    "media": asset_urn,
                    "title": {"text": "Test Ad"}
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    r = requests.post(url, headers={**bearer(access_token), "Content-Type":"application/json"}, json=payload, timeout=30)
    r.raise_for_status()
    return r.headers["x-restli-id"]

def create_image_creative(access_token, account_urn, ugc_urn):
    url = "https://api.linkedin.com/v2/adCreativesV2"
    payload = {
        "account": account_urn,
        "type": "IMAGE",
        "reference": ugc_urn
    }
    r = requests.post(url, headers={**bearer(access_token), "Content-Type":"application/json"}, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("urn") or data.get("id")

def get_preview(access_token, account_urn, creative_urn):
    url = "https://api.linkedin.com/v2/adPreviews"
    params = {"account": account_urn, "creative": creative_urn}
    r = requests.get(url, headers=bearer(access_token), params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    # 1) Get fresh token
    access_token = get_access_token()
    print("Access token acquired.")

    # 2) Read asset_urn saved by upload script
    asset_urn = Path(__file__).with_name("last_asset_urn.txt").read_text(encoding="utf-8").strip()
    print("Using asset:", asset_urn)

    # 3) Create UGC post
    ugc_urn = create_ugc_post(access_token, ORG_URN, asset_urn)
    print("UGC post created:", ugc_urn)

    # 4) Create image creative
    creative_urn = create_image_creative(access_token, ACCOUNT_ID, ugc_urn)
    print("Creative created:", creative_urn)

    # 5) Request preview
    preview = get_preview(access_token, ACCOUNT_ID, creative_urn)
    print(json.dumps(preview, indent=2))

if __name__ == "__main__":
    main()
