import os
import sys

import requests

GRAPH_HOST = os.getenv("META_GRAPH_HOST", "https://graph.facebook.com").rstrip("/")
API_VERSION = os.getenv("META_API_VERSION", "v23.0")
IG_USER_ID = os.getenv("IG_USER_ID", "").strip()
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()


def get_json(url, params):
    response = requests.get(url, params=params, timeout=60)
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if not response.ok:
        raise RuntimeError(f"Meta API error {response.status_code}: {payload}")
    return payload


def main():
    if not IG_USER_ID:
        raise RuntimeError("Missing IG_USER_ID")
    if not ACCESS_TOKEN:
        raise RuntimeError("Missing META_ACCESS_TOKEN")

    profile = get_json(
        f"{GRAPH_HOST}/{API_VERSION}/{IG_USER_ID}",
        {
            "fields": "id,username,account_type",
            "access_token": ACCESS_TOKEN,
        },
    )

    print("Meta connection OK")
    print(f"Instagram user id: {profile.get('id')}")
    print(f"Username: @{profile.get('username')}")
    print(f"Account type: {profile.get('account_type')}")

    try:
        limit = get_json(
            f"{GRAPH_HOST}/{API_VERSION}/{IG_USER_ID}/content_publishing_limit",
            {
                "fields": "quota_usage,config",
                "access_token": ACCESS_TOKEN,
            },
        )
        print(f"Publishing limit response: {limit}")
    except Exception as exc:
        print(f"Publishing-limit check warning: {exc}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
