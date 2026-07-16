"""
Get LinkedIn Person URN
-------------------------
Reads LINKEDIN_ACCESS_TOKEN from .env (avoids shell copy-paste issues
with special characters in the token) and fetches your Person ID.

Run:
    python get_linkedin_urn.py
"""

import os
from dotenv import load_dotenv
import requests

load_dotenv()

token = os.getenv("LINKEDIN_ACCESS_TOKEN")

if not token:
    raise SystemExit("ERROR: LINKEDIN_ACCESS_TOKEN not found in .env")

response = requests.get(
    "https://api.linkedin.com/v2/userinfo",
    headers={"Authorization": f"Bearer {token}"}
)

print(f"Status code: {response.status_code}")
print(response.json())
