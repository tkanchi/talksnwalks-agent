"""Publish an image carousel through the Instagram API.

Kept separate from publish_instagram.py so existing Reel/single-image publishing
remains untouched. Expects 2-10 publicly reachable image URLs.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

GRAPH_HOST = os.getenv("META_GRAPH_HOST", "https://graph.instagram.com").rstrip("/")
API_VERSION = os.getenv("META_API_VERSION", "v26.0")
IG_USER_ID = os.getenv("IG_USER_ID", "").strip()
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
IMAGE_URLS = [item.strip() for item in os.getenv("CAROUSEL_IMAGE_URLS", "").split(",") if item.strip()]
URLS_FILE = Path(os.getenv("CAROUSEL_URLS_FILE", "outputs/carousels/image_urls.txt"))
CAPTION_FILE = Path(os.getenv("CAPTION_FILE", "outputs/carousels/caption.txt"))
RESULT_FILE = Path(os.getenv("RESULT_FILE", "outputs/carousels/publish_result.json"))


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
        raise RuntimeError(f"Instagram API error {response.status_code}: {safe}")
    return payload


def wait_until_ready(container_id, timeout_seconds=300):
    url = f"{GRAPH_HOST}/{API_VERSION}/{container_id}"
    deadline = time.time() + timeout_seconds
    last = None
    while time.time() < deadline:
        payload = request_json(
            "GET",
            url,
            params={"fields": "status_code,status", "access_token": ACCESS_TOKEN},
        )
        last = payload
        status = payload.get("status_code", "")
        print(f"Container {container_id} status: {status}")
        if status in {"FINISHED", "PUBLISHED"}:
            return payload
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Container failed: {payload}")
        time.sleep(10)
    raise TimeoutError(f"Container was not ready within {timeout_seconds}s. Last status: {last}")


def create_child(image_url):
    payload = request_json(
        "POST",
        f"{GRAPH_HOST}/{API_VERSION}/{IG_USER_ID}/media",
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": ACCESS_TOKEN,
        },
    )
    child_id = payload.get("id")
    if not child_id:
        raise RuntimeError(f"Instagram did not return a child container id: {payload}")
    return child_id


def create_parent(child_ids, caption):
    payload = request_json(
        "POST",
        f"{GRAPH_HOST}/{API_VERSION}/{IG_USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },
    )
    parent_id = payload.get("id")
    if not parent_id:
        raise RuntimeError(f"Instagram did not return a carousel container id: {payload}")
    return parent_id


def publish(parent_id):
    payload = request_json(
        "POST",
        f"{GRAPH_HOST}/{API_VERSION}/{IG_USER_ID}/media_publish",
        data={"creation_id": parent_id, "access_token": ACCESS_TOKEN},
    )
    media_id = payload.get("id")
    if not media_id:
        raise RuntimeError(f"Instagram did not return a published media id: {payload}")
    return media_id


def load_urls():
    urls = list(IMAGE_URLS)
    if not urls and URLS_FILE.exists():
        urls = [line.strip() for line in URLS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not 2 <= len(urls) <= 10:
        raise RuntimeError(f"Carousel requires 2-10 image URLs; found {len(urls)}")
    return urls


def main():
    require("IG_USER_ID", IG_USER_ID)
    require("META_ACCESS_TOKEN", ACCESS_TOKEN)
    urls = load_urls()
    if not CAPTION_FILE.exists():
        raise FileNotFoundError(f"Caption file not found: {CAPTION_FILE}")
    caption = CAPTION_FILE.read_text(encoding="utf-8").strip()

    child_ids = []
    for index, image_url in enumerate(urls, start=1):
        print(f"Creating carousel child {index}/{len(urls)}...")
        child_id = create_child(image_url)
        wait_until_ready(child_id)
        child_ids.append(child_id)

    print("Creating carousel parent container...")
    parent_id = create_parent(child_ids, caption)
    wait_until_ready(parent_id)

    print("Publishing Instagram carousel...")
    media_id = publish(parent_id)
    print(f"Published Instagram carousel media id: {media_id}")

    result = {
        "status": "PUBLISHED",
        "media_type": "CAROUSEL",
        "parent_container_id": parent_id,
        "child_container_ids": child_ids,
        "media_id": media_id,
        "image_urls": urls,
    }
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
