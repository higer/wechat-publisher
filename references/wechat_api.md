# WeChat MP API Quick Reference

## Authentication

- Endpoint: `GET https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET`
- Returns: `{ "access_token": "...", "expires_in": 7200 }`
- Token valid for 2 hours; cache and refresh proactively

## Image Upload

### Permanent material (for cover images)
- Endpoint: `POST https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=TOKEN&type=image`
- Body: multipart/form-data with field `media`
- Returns: `{ "media_id": "...", "url": "..." }`
- Limits: 5000 images total per account

### Article body images
- Endpoint: `POST https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=TOKEN`
- Body: multipart/form-data with field `media`
- Returns: `{ "url": "..." }`
- URL can be used directly in `<img src="...">` within article HTML

## Draft Management

### Create draft
- Endpoint: `POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=TOKEN`
- Body:
```json
{
  "articles": [{
    "title": "标题",
    "author": "作者",
    "digest": "摘要（不超过120字）",
    "content": "<p>正文HTML</p>",
    "thumb_media_id": "封面图media_id",
    "need_open_comment": 1,
    "only_fans_can_comment": 0
  }]
}
```
- Returns: `{ "media_id": "draft_media_id" }`

## Content Rules

- HTML must use **inline CSS only** — no `<style>` or `<link>` tags
- No external JS — all `<script>` tags are stripped
- Images must be uploaded to WeChat CDN — external image URLs will be blocked
- Max content length: ~20,000 characters of HTML
- Cover image recommended size: 900×383 px (2.35:1 ratio)
- Content image max: 1080px width
- Supported image formats: PNG, JPEG, GIF (≤10MB)

## Error Codes

| Code  | Meaning                        |
|-------|--------------------------------|
| 40001 | Invalid access_token           |
| 40004 | Invalid media type             |
| 45008 | Article content too long       |
| 45009 | API call frequency limit       |
| 45028 | No publishing permission       |
| 48001 | API not authorized for account |

## Doubao Seedream Image Generation API

### Overview
- Provider: Volcengine ARK (火山方舟)
- Model: `doubao-seedream-5-0-260128` (Seedream 5.0 lite)
- Endpoint: `POST https://ark.cn-beijing.volces.com/api/v3/images/generations`
- Auth: `Authorization: Bearer <ARK_API_KEY>`
- API Key: obtain from [console.volcengine.com/ark → API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey)

### Request body
```json
{
  "model": "doubao-seedream-5-0-260128",
  "prompt": "提示词，支持中英文",
  "size": "2048x2048",
  "response_format": "b64_json",
  "watermark": false
}
```

### Key parameters
- `size`: pixel dimensions `WxH` or resolution keyword (`2K`, `4K`)
  - 5.0 lite: min 2560×1440 (3.69M px), max 4096×4096 (16.78M px)
  - Recommended: `2048x2048` (1:1), `2304x1728` (4:3), `2848x1600` (16:9)
- `response_format`: `"url"` (24h expiry) or `"b64_json"`
- `watermark`: `true` adds "AI生成" watermark; `false` to disable
- `sequential_image_generation`: `"auto"` for multi-image sets, `"disabled"` for single image

### Response
```json
{
  "model": "doubao-seedream-5-0-260128",
  "created": 1757321139,
  "data": [{ "b64_json": "...", "size": "2048x2048" }],
  "usage": { "generated_images": 1, "output_tokens": 16384, "total_tokens": 16384 }
}
```

### Available models
| Model ID | Notes |
|----------|-------|
| `doubao-seedream-5-0-260128` | Seedream 5.0 lite — highest quality, supports web search |
| `doubao-seedream-4.5` | Good quality, supports 1K/2K/4K |
| `doubao-seedream-4.0` | Stable, supports 2K/3K |
| `doubao-seedream-3.0-t2i` | Text-to-image only, min 512×512 |
