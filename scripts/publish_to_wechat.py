#!/usr/bin/env python3
"""
WeChat Official Account Publisher
Handles: access token, image upload, and draft creation via WeChat MP API.

Usage:
    python publish_to_wechat.py \
        --config .wx_config.json \
        --html article.html \
        --title "文章标题" \
        --author "作者名" \
        --digest "文章摘要" \
        --cover cover.png \
        [--content-images img1.png img2.png]

Config file format (.wx_config.json):
{
    "app_id": "your_app_id",
    "app_secret": "your_app_secret"
}
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import mimetypes
import uuid


# --- Token Management ---

TOKEN_CACHE_FILE = ".wx_token_cache.json"


def get_access_token(app_id: str, app_secret: str) -> str:
    """Obtain access_token, using cache if still valid."""
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache = json.load(f)
        if cache.get("expires_at", 0) > time.time() + 60:
            return cache["access_token"]

    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    )
    resp = urllib.request.urlopen(url, timeout=15)
    data = json.loads(resp.read().decode())
    if "access_token" not in data:
        print(f"[ERROR] Failed to get access_token: {data}", file=sys.stderr)
        sys.exit(1)

    cache = {
        "access_token": data["access_token"],
        "expires_at": time.time() + data.get("expires_in", 7200),
    }
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump(cache, f)
    return data["access_token"]


# --- Multipart Upload Helper ---

def _build_multipart(fields: dict, files: dict) -> tuple:
    """Build multipart/form-data body. Returns (content_type, body_bytes)."""
    boundary = uuid.uuid4().hex
    lines = []
    for key, value in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"'.encode())
        lines.append(b"")
        lines.append(value.encode() if isinstance(value, str) else value)
    for key, (filename, filedata, content_type) in files.items():
        lines.append(f"--{boundary}".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode()
        )
        lines.append(f"Content-Type: {content_type}".encode())
        lines.append(b"")
        lines.append(filedata)
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = b"\r\n".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return content_type, body


# --- Image Upload ---

def upload_image(access_token: str, image_path: str, media_type: str = "image") -> str:
    """
    Upload image to WeChat. Returns media_id (for cover) or url (for content images).
    media_type: 'image' for permanent material, 'news_image' for article body images.
    """
    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    mime = mimetypes.guess_type(image_path)[0] or "image/png"
    filename = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        filedata = f.read()

    if media_type == "news_image":
        # Upload for article body — returns URL
        url = (
            "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
            f"?access_token={access_token}"
        )
    else:
        # Upload as permanent material — returns media_id
        url = (
            "https://api.weixin.qq.com/cgi-bin/material/add_material"
            f"?access_token={access_token}&type=image"
        )

    content_type, body = _build_multipart({}, {"media": (filename, filedata, mime)})
    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", content_type)

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Upload failed: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    if "errcode" in data and data["errcode"] != 0:
        print(f"[ERROR] Upload error: {data}", file=sys.stderr)
        sys.exit(1)

    if media_type == "news_image":
        result = data.get("url", "")
        print(f"[OK] Content image uploaded: {result}")
        return result
    else:
        result = data.get("media_id", "")
        print(f"[OK] Cover image uploaded, media_id: {result}")
        return result


# --- Draft Creation ---

def create_draft(
    access_token: str,
    title: str,
    author: str,
    digest: str,
    content_html: str,
    cover_media_id: str,
) -> str:
    """Create a draft article in WeChat MP backend. Returns media_id of the draft."""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    payload = {
        "articles": [
            {
                "title": title,
                "author": author,
                "digest": digest,
                "content": content_html,
                "thumb_media_id": cover_media_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }
        ]
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    req.add_header("Content-Type", "application/json; charset=utf-8")

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Draft creation failed: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    if "errcode" in result and result["errcode"] != 0:
        print(f"[ERROR] Draft error: {result}", file=sys.stderr)
        sys.exit(1)

    media_id = result.get("media_id", "")
    print(f"[OK] Draft created, media_id: {media_id}")
    return media_id


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Publish article to WeChat MP draft box")
    parser.add_argument("--config", required=True, help="Path to .wx_config.json")
    parser.add_argument("--html", required=True, help="Path to rendered HTML file")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--digest", default="", help="Article digest/summary")
    parser.add_argument("--cover", required=True, help="Path to cover image")
    parser.add_argument("--content-images", nargs="*", default=[], help="Paths to content images")
    args = parser.parse_args()

    # Load config
    with open(args.config, "r") as f:
        config = json.load(f)
    app_id = config["app_id"]
    app_secret = config["app_secret"]

    # Get token
    print("[STEP 1] Obtaining access token...")
    token = get_access_token(app_id, app_secret)

    # Upload cover image
    print("[STEP 2] Uploading cover image...")
    cover_media_id = upload_image(token, args.cover, media_type="image")

    # Upload content images and replace placeholders in HTML
    html_content = open(args.html, "r", encoding="utf-8").read()
    if args.content_images:
        print("[STEP 3] Uploading content images...")
        for i, img_path in enumerate(args.content_images):
            img_url = upload_image(token, img_path, media_type="news_image")
            placeholder = f"{{{{CONTENT_IMAGE_{i+1}}}}}"
            html_content = html_content.replace(placeholder, img_url)
    else:
        print("[STEP 3] No content images to upload, skipping.")

    # Create draft
    print("[STEP 4] Creating draft...")
    draft_id = create_draft(
        access_token=token,
        title=args.title,
        author=args.author,
        digest=args.digest,
        content_html=html_content,
        cover_media_id=cover_media_id,
    )

    print(f"\n✅ Done! Draft published with media_id: {draft_id}")
    print("Go to https://mp.weixin.qq.com to preview and publish.")


if __name__ == "__main__":
    main()
