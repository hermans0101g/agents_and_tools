# upload_linkedin_image.py
# Requires: pip install requests

import os
import json
import requests
from pathlib import Path

# ---------- CONFIG ----------
CLIENT_ID = "78t0rea15rmplv"
CLIENT_SECRET = "WPL_AP1.csr2KEfrWpoLQ9H9.H5mzsA=="
REDIRECT_URI = "http://localhost:8000"  # must match your LinkedIn app config exactly
ACCOUNT_ID = "urn:li:sponsoredAccount:515449142"

# local image path
IMAGE_PATH = r"C:\repos\agents_and_tools\data\tenxdiversify.jpg"
# ----------------------------

AUTH_URL = (
    "https://www.linkedin.com/oauth/v2/authorization"
    f"?response_type=code&client_id={CLIENT_ID}"
    f"&redirect_uri={requests.utils.quote(REDIRECT_URI, safe='')}"
    "&scope=r_ads%20rw_ads"
)
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
REGISTER_UPLOAD_URL = "https://api.linkedin.com/v2/assets?action=registerUpload"


def get_access_token(auth_code: str) -> str:
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Token exchange failed: {resp.status_code} {resp.text}")
    token = resp.json()["access_token"]
    return token


def register_image_upload(access_token: str, account_urn: str):
    """
    Returns (upload_url, asset_urn).
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "registerUploadRequest": {
            "owner": account_urn,
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }
    resp = requests.post(
        REGISTER_UPLOAD_URL, headers=headers, data=json.dumps(payload), timeout=30
    )
    if not resp.ok:
        raise RuntimeError(f"Register upload failed: {resp.status_code} {resp.text}")

    data = resp.json()["value"]
    asset_urn = data["asset"]
    upload_url = data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]

    return upload_url, asset_urn


def upload_binary(upload_url: str, file_path: str):
    """
    Uploads the image bytes to the pre-signed URL.
    LinkedIn's uploadUrl is pre-authorized; do NOT include Bearer auth.
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {file_path}")

    with p.open("rb") as f:
        # Content-Type can be image/jpeg (or application/octet-stream)
        headers = {"Content-Type": "application/octet-stream"}
        resp = requests.put(upload_url, data=f, headers=headers, timeout=120)

    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"Binary upload failed: {resp.status_code} {resp.text}")


def main():
    print("1) Authorize the application")
    print("Open this URL and approve access (scopes: r_ads, rw_ads):")
    print(AUTH_URL)
    print()
    auth_code = input("Paste the 'code' from the redirect URL here: ").strip()

    print("\n2) Exchanging code for access token...")
    access_token = get_access_token(auth_code)
    print("Access token acquired.")

    print("\n3) Registering image upload (Assets API)...")
    upload_url, asset_urn = register_image_upload(access_token, ACCOUNT_ID)
    print(f"Upload URL received.")
    print(f"Proposed asset URN: {asset_urn}")

    print("\n4) Uploading local image bytes...")
    upload_binary(upload_url, IMAGE_PATH)
    print("Upload complete ✅")

    print("\n=== RESULT ===")
    print(f"Image asset URN (use this in your ad creative/preview): {asset_urn}")
    print("================\n")

    # Optional: write to a small file for your pipeline
    out = Path(__file__).with_name("last_asset_urn.txt")
    out.write_text(asset_urn, encoding="utf-8")
    print(f"Saved URN to: {out}")


if __name__ == "__main__":
    main()
