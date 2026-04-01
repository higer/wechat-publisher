#!/usr/bin/env python3
"""
Generate images for WeChat articles using external AI image APIs.

Supported providers:
  - doubao   : Doubao Seedream 5.0 lite (requires Volcengine ARK API key)
  - openai   : DALL-E 3 (requires OpenAI API key)
  - stability: Stability AI SDXL (requires Stability API key)

Usage:
    python generate_images.py \
        --config .wx_config.json \
        --prompts "prompt for cover" "prompt for img1" "prompt for img2" \
        --sizes 900x383 1080x720 1080x720 \
        --output-dir ./images

If no image_api config is found, generates prompt files (.txt) as fallback.
"""

import argparse
import json
import os
import sys
import base64
import urllib.request
import urllib.error


def generate_doubao(api_key: str, prompt: str, size: str, **kwargs) -> bytes:
    """Generate image via Doubao Seedream (Volcengine ARK). Returns image bytes."""
    import math

    model = kwargs.get("model", "doubao-seedream-5-0-260128")

    # Seedream recommended sizes (ratio -> WxH) at 2K resolution
    RECOMMENDED = {
        (1, 1): (2048, 2048),
        (4, 3): (2304, 1728),
        (3, 4): (1728, 2304),
        (16, 9): (2848, 1600),
        (9, 16): (1600, 2848),
        (3, 2): (2496, 1664),
        (2, 3): (1664, 2496),
        (21, 9): (3136, 1344),
    }

    w, h = map(int, size.split("x"))
    ratio = w / h

    # Find closest recommended size by aspect ratio
    best_key = None
    best_diff = float("inf")
    for (rw, rh) in RECOMMENDED:
        diff = abs(ratio - rw / rh)
        if diff < best_diff:
            best_diff = diff
            best_key = (rw, rh)

    # If close enough to a standard ratio, use the recommended size directly
    if best_diff < 0.15:
        sw, sh = RECOMMENDED[best_key]
    else:
        # Custom ratio: scale up to meet minimum pixel requirement
        MIN_PX = 3686400
        total_px = w * h
        if total_px < MIN_PX:
            scale = math.ceil(math.sqrt(MIN_PX / total_px) * 100) / 100  # round up
            w = math.ceil(w * scale)
            h = math.ceil(h * scale)
        # Ensure even numbers (some models prefer it)
        w = w if w % 2 == 0 else w + 1
        h = h if h % 2 == 0 else h + 1
        # Final safety check
        while w * h < MIN_PX:
            w += 2
        sw, sh = w, h

    seedream_size = f"{sw}x{sh}"
    print(f"  Seedream size: {size} -> {seedream_size} ({sw*sh:,} px)")

    url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "size": seedream_size,
        "response_format": "b64_json",
        "watermark": False,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        resp = urllib.request.urlopen(req, timeout=180)
        data = json.loads(resp.read().decode())
        b64 = data["data"][0]["b64_json"]
        return base64.b64decode(b64)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[ERROR] Doubao Seedream API error: {e.code} {body}", file=sys.stderr)
        sys.exit(1)


def generate_openai(api_key: str, prompt: str, size: str, **kwargs) -> bytes:
    """Generate image via OpenAI DALL-E 3. Returns PNG bytes."""
    # Map to nearest supported DALL-E 3 size
    w, h = map(int, size.split("x"))
    ratio = w / h
    if ratio > 1.5:
        dalle_size = "1792x1024"
    elif ratio < 0.7:
        dalle_size = "1024x1792"
    else:
        dalle_size = "1024x1024"

    url = "https://api.openai.com/v1/images/generations"
    payload = json.dumps({
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": dalle_size,
        "response_format": "b64_json",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read().decode())
        b64 = data["data"][0]["b64_json"]
        return base64.b64decode(b64)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[ERROR] OpenAI API error: {e.code} {body}", file=sys.stderr)
        sys.exit(1)


def generate_stability(api_key: str, prompt: str, size: str, **kwargs) -> bytes:
    """Generate image via Stability AI. Returns PNG bytes."""
    w, h = map(int, size.split("x"))
    # Stability requires dimensions as multiples of 64
    w = max(512, (w // 64) * 64)
    h = max(512, (h // 64) * 64)
    # Cap at 1536
    w = min(w, 1536)
    h = min(h, 1536)

    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    payload = json.dumps({
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 7,
        "width": w,
        "height": h,
        "samples": 1,
        "steps": 30,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read().decode())
        b64 = data["artifacts"][0]["base64"]
        return base64.b64decode(b64)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[ERROR] Stability API error: {e.code} {body}", file=sys.stderr)
        sys.exit(1)


def fallback_prompt_only(prompt: str, output_path: str):
    """When no API is configured, save prompt as .txt for manual image creation."""
    txt_path = output_path.rsplit(".", 1)[0] + ".prompt.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Image prompt:\n{prompt}\n\nReplace {os.path.basename(output_path)} with a generated image.\n")
    print(f"[FALLBACK] No image API configured. Prompt saved to: {txt_path}")


GENERATORS = {
    "doubao": generate_doubao,
    "openai": generate_openai,
    "stability": generate_stability,
}


def main():
    parser = argparse.ArgumentParser(description="Generate article images via AI API")
    parser.add_argument("--config", required=True, help="Path to .wx_config.json")
    parser.add_argument("--prompts", nargs="+", required=True, help="Image prompts (one per image)")
    parser.add_argument("--sizes", nargs="+", required=True, help="Image sizes as WxH (one per image)")
    parser.add_argument("--output-dir", default=".", help="Output directory for images")
    parser.add_argument("--names", nargs="+", default=None, help="Output filenames (default: cover.png, content_1.png, content_2.png)")
    args = parser.parse_args()

    if len(args.prompts) != len(args.sizes):
        print("[ERROR] Number of prompts must match number of sizes", file=sys.stderr)
        sys.exit(1)

    # Default output names
    if args.names:
        names = args.names
    else:
        names = ["cover.png"] + [f"content_{i}.png" for i in range(1, len(args.prompts))]

    os.makedirs(args.output_dir, exist_ok=True)

    # Load config
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    image_cfg = config.get("image_api", {})
    provider = image_cfg.get("provider", "")
    api_key = image_cfg.get("api_key", "")
    extra_opts = {k: v for k, v in image_cfg.items() if k not in ("provider", "api_key")}

    generator = GENERATORS.get(provider) if provider and api_key else None

    for i, (prompt, size, name) in enumerate(zip(args.prompts, args.sizes, names)):
        output_path = os.path.join(args.output_dir, name)
        print(f"\n[IMAGE {i+1}/{len(args.prompts)}] {name} ({size})")
        print(f"  Prompt: {prompt[:80]}...")

        if generator:
            print(f"  Using provider: {provider}")
            img_bytes = generator(api_key, prompt, size, **extra_opts)
            with open(output_path, "wb") as f:
                f.write(img_bytes)
            print(f"  [OK] Saved to {output_path} ({len(img_bytes)} bytes)")
        else:
            fallback_prompt_only(prompt, output_path)

    if not generator:
        print("\n⚠️  No image API configured. To enable AI image generation, add to .wx_config.json:")
        print('  "image_api": { "provider": "doubao", "api_key": "your-ark-api-key" }')
        print('  Supported providers: "doubao" (Seedream), "openai" (DALL-E 3), "stability" (SDXL)')


if __name__ == "__main__":
    main()
