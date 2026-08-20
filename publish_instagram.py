import json
import os
import sys
import time
from pathlib import Path

import requests

GRAPH_HOST = os.getenv("META_GRAPH_HOST", "https://graph.facebook.com").rstrip("/")
API_VERSION = os.getenv("META_API_VERSION", "v23.0")
IG_USER_ID = os.getenv("IG_USER_ID", "").strip()
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
VIDEO_URL = os.getenv("VIDEO_URL", "").strip()
CAPTION_FILE = Path(os.getenv("CAPTION_FILE", "outputs/caption.txt"))
RESULT_FILE = Path(os.getenv("RESULT_FILE", "outputs/publish_result.json"))
SHARE_TO_FEED = os.getenv("SHARE_TO_FEED", "true").lower() == "true"


def require(name, value):
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")


def request_json(method, url, **kwargs):
    response = requests.request(method, url, timeout=60, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if not response.ok:
        safe = dict(payload)
        if "access_token" in safe:
            safe["access_token"] = "***"
        raise RuntimeError(f"Meta API error {response.status_code}: {safe}")
    return payload


def create_container(caption):
    url = f"{GRAPH_HOST}/{API_VERSION}/{IG_USER_ID}/media"
    data = {
        "media_type": "REELS",
        "video_url": VIDEO_URL,
        "caption": caption,
        "share_to_feed": "true" if SHARE_TO_FEED else "false",
        "access_token": ACCESS_TOKEN,
    }
    payload = request_json("POST", url, data=data)
    container_id = payload.get("id")
    if not container_id:
        raise RuntimeError(f"Meta did not return a container id: {payload}")
    return container_id


def wait_until_ready(container_id, timeout_seconds=300):
    url = f"{GRAPH_HOST}/{API_VERSION}/{container_id}"
    deadline = time.time() + timeout_seconds
    last = None

    while time.time() < deadline:
        payload = request_json(
            "GET",
            url,
            params={
                "fields": "status_code,status",
                "access_token": ACCESS_TOKEN,
            },
        )
        last = payload
        status = payload.get("status_code", "")
        print(f"Container status: {status}")

        if status in {"FINISHED", "PUBLISHED"}:
            return payload
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Container failed: {payload}")

        time.sleep(20)

    raise TimeoutError(f"Container was not ready within {timeout_seconds}s. Last status: {last}")


def publish(container_id):
    url = f"{GRAPH_HOST}/{API_VERSION}/{IG_USER_ID}/media_publish"
    payload = request_json(
        "POST",
        url,
        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },
    )
    media_id = payload.get("id")
    if not media_id:
        raise RuntimeError(f"Meta did not return a published media id: {payload}")
    return media_id


def main():
    require("IG_USER_ID", IG_USER_ID)
    require("META_ACCESS_TOKEN", ACCESS_TOKEN)
    require("VIDEO_URL", VIDEO_URL)

    if not CAPTION_FILE.exists():
        raise FileNotFoundError(f"Caption file not found: {CAPTION_FILE}")

    caption = CAPTION_FILE.read_text(encoding="utf-8").strip()
    print("Creating Instagram Reel container...")
    container_id = create_container(caption)
    print(f"Container created: {container_id}")

    wait_until_ready(container_id)
    print("Publishing Reel...")
    media_id = publish(container_id)
    print(f"Published Instagram media id: {media_id}")

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(
        json.dumps(
            {
                "status": "PUBLISHED",
                "container_id": container_id,
                "media_id": media_id,
                "video_url": VIDEO_URL,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
