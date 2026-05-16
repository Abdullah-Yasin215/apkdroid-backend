import requests
import json
import base64
from nacl import encoding, public

# Config
TOKEN = "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
OWNER = "Abdullah-Yasin215"
REPO = "apkdroid-project"

headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# 1. Get public key
url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/public-key"
res = requests.get(url, headers=headers)
if res.status_code != 200:
    print("Error getting public key:", res.json())
    exit(1)

key_data = res.json()
key_id = key_data["key_id"]
pub_key = key_data["key"]

def encrypt(public_key: str, secret_value: str) -> str:
    public_key_bytes = base64.b64decode(public_key)
    sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def set_secret(secret_name, secret_value):
    encrypted_value = encrypt(pub_key, secret_value)
    data = {"encrypted_value": encrypted_value, "key_id": key_id}
    res = requests.put(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/{secret_name}",
        headers=headers,
        json=data
    )
    if res.status_code in [201, 204]:
        print(f"Secret {secret_name} set successfully.")
    else:
        print(f"Failed to set {secret_name}:", res.json())

# Assuming ADMIN_API_KEY from .env
import os
with open(".env", "r") as f:
    env_content = f.read()

admin_key = ""
for line in env_content.splitlines():
    if line.startswith("ADMIN_API_KEY="):
        admin_key = line.split("=", 1)[1].strip("'\"")

if admin_key:
    set_secret("ADMIN_API_KEY", admin_key)
    set_secret("API_BASE_URL", "https://api.apkdroid.net") # Assuming future production domain, but can be updated later
else:
    print("ADMIN_API_KEY not found in .env")

