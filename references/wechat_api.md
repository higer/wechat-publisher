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
