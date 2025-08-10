import requests
import json

CLIENT_ID = "78t0rea15rmplv"
CLIENT_SECRET = "WPL_AP1.csr2KEfrWpoLQ9H9.H5mzsA=="
ACCOUNT_ID = "urn:li:sponsoredAccount:515449142"  # Example format
CAMPAIGN_ID = "urn:li:sponsoredCampaign:407014464"  # Existing campaign for preview
REDIRECT_URI = "http://localhost:8000"  # Use the same redirect URI as in your LinkedIn app settings

# --- Step 1: Get Authorization Code ---
print(f"Open this URL in your browser to authorize:\n"
      f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={CLIENT_ID}"
      f"&redirect_uri={REDIRECT_URI}&scope=r_ads%20rw_ads\n")
auth_code = input("Paste the 'code' parameter from the redirected URL here: ").strip()

# --- Step 2: Exchange for Access Token ---
token_url = "https://www.linkedin.com/oauth/v2/accessToken"
token_data = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}
token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
token_res = requests.post(token_url, data=token_data, headers=token_headers)
access_token = token_res.json()["access_token"]

print("✅ Access token acquired!")

# --- Step 3: Create Ad Preview (text only for simplicity) ---
preview_url = "https://api.linkedin.com/v2/adPreviews"
headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

# Ad creative data (simple single image ad for preview)
ad_creative = {
    "variables": {
        "account": ACCOUNT_ID,
        "campaign": CAMPAIGN_ID,
        "creative": {
            "name": "Test Ad Preview",
            "type": "SPONSORED_UPDATES",
            "variables": {
                "shareContent": {
                    "shareCommentary": {
                        "text": "Let us craft your diversification strategy."
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "description": {
                                "text": "This is a test ad image"
                            },
                            "media": "urn:li:digitalmediaAsset:D4E22AQElcBXI6_Z_ZA",  # Pre-uploaded image asset
                            "title": {
                                "text": "Let us craft your diversification strategy."
                            }
                        }
                    ]
                }
            }
        }
    }
}



# Send ad preview request
preview_url = "https://api.linkedin.com/v2/adPreviews"
response = requests.post(preview_url, headers=headers, data=json.dumps(ad_creative))

# Show result
if response.status_code == 201 or response.status_code == 200:
    print("✅ Ad preview created successfully!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"❌ Error {response.status_code}: {response.text}")
