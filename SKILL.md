---
name: wechat-publisher
description: >
  Auto-generate and publish WeChat Official Account (微信公众号) articles to the draft box.
  Use this skill when the user wants to: create a WeChat MP article with a given title,
  generate AI cover and content images for the article, format an article for WeChat MP
  with proper Markdown and Front Matter, publish/upload an article to WeChat MP draft box,
  or do any combination of these steps. Triggers include: 公众号, 微信文章, WeChat article,
  MP article, 发公众号, 写公众号文章, 公众号排版, 公众号草稿, publish to WeChat, generate
  WeChat post, 自媒体文章. Also triggers for casual phrasing like "帮我写一篇公众号文",
  "发一篇文章到公众号", "生成公众号配图".
---

# WeChat Publisher

Generate and publish WeChat Official Account articles to the draft box. The workflow covers
article writing, AI image generation, Markdown formatting, HTML conversion, and WeChat API
publishing.

## Configuration

All config lives in `.wx_config.json`, located in the **current working directory** (the directory where the skill is invoked). If the file does not exist, ask the user for credentials and create it.

```json
{
  "app_id": "your_wechat_app_id",
  "app_secret": "your_wechat_app_secret",
  "image_api": {
    "provider": "doubao",
    "api_key": "your-ark-api-key"
  }
}
```

Fields:
- `app_id` / `app_secret` (required for publishing): WeChat MP credentials, obtain from [mp.weixin.qq.com](https://mp.weixin.qq.com) → 开发 → 基本配置
- `image_api` (optional): AI image generation config
  - `provider`: `"doubao"` (Seedream 5.0 lite, recommended), `"openai"` (DALL-E 3), or `"stability"` (Stability AI SDXL)
  - `api_key`: the corresponding API key
  - `model` (optional, doubao only): override model ID, default `doubao-seedream-5-0-260128`
  - If omitted, the skill falls back to MuleRun built-in `mulerouter-skills` (when available) or generates prompt text files for manual image creation

## Workflow Overview

1. **Generate article** — Write a Markdown article with Front Matter based on user's title and style
2. **Generate images** — Create 1 cover (900×383) + 2 content images via AI (multi-provider)
3. **Convert to HTML** — Run `scripts/md_to_html.py` to produce inline-styled HTML for WeChat
4. **Publish to draft** — Run `scripts/publish_to_wechat.py` to upload images and create draft

## Step 1: Generate Article

Read `references/article_styles.md` for style definitions and writing rules.

Accept these parameters from the user (ask if not provided):
- **title** (required): Article title
- **style** (optional, default "tech"): One of `tech`, `business`, `lifestyle`, `education`, `opinion`
- **author** (optional): Author name for byline

Generate a Markdown file with this structure:

```markdown
---
title: "用户指定的标题"
author: "作者名"
date: "YYYY-MM-DD"
style: "tech"
digest: "120字以内的摘要"
tags:
  - 标签1
  - 标签2
cover: "cover.png"
content_images:
  - "content_1.png"
  - "content_2.png"
---

# 标题

正文内容...

![图片描述1]({{CONTENT_IMAGE_1}})

更多正文...

![图片描述2]({{CONTENT_IMAGE_2}})

结尾段落...
```

Rules:
- Total length: 2000-4000 Chinese characters
- Use `{{CONTENT_IMAGE_1}}` and `{{CONTENT_IMAGE_2}}` as image placeholders
- Place first image at ~30% of article, second at ~70%
- Include subheadings (##) every 300-500 characters

## Step 2: Generate Images

Generate 3 images: 1 cover + 2 content images. The generation strategy depends on the environment:

### Provider priority

1. **External API** (if `image_api` configured in `.wx_config.json`): run `scripts/generate_images.py`
2. **MuleRun built-in** (if `mulerouter-skills` is available): use it directly
3. **Fallback**: `scripts/generate_images.py` saves `.prompt.txt` files with detailed prompts for manual creation

### Using generate_images.py (external API or fallback)

```bash
python scripts/generate_images.py \
  --config .wx_config.json \
  --prompts "cover prompt here" "content image 1 prompt" "content image 2 prompt" \
  --sizes 900x383 1080x720 1080x720 \
  --output-dir ./images \
  --names cover.png content_1.png content_2.png
```

### Using mulerouter-skills (MuleRun environment)

Call `mulerouter-skills` directly to generate each image with the prompts below.

### Image specifications

| Image | Size | Filename |
|-------|------|----------|
| Cover | 900×383 (2.35:1) | `cover.png` |
| Content 1 | 1080×720 (3:2) | `content_1.png` |
| Content 2 | 1080×720 (3:2) | `content_2.png` |

### Prompt guidelines
- Derive cover prompt from article title; content prompts from surrounding paragraphs
- Be specific: scene, lighting, color palette, art style
- Always include "no text, no watermark" for clean output
- Tech articles: "flat illustration, clean lines, soft gradients, modern tech aesthetic"
- Lifestyle: "warm photography, natural lighting, shallow depth of field"
- Business: "professional, data visualization, corporate blue tones"

## Step 3: Convert to HTML

Run the Markdown-to-HTML converter:

```bash
python scripts/md_to_html.py article.md -o article.html --theme default
```

This produces WeChat-compatible HTML with inline CSS. The converter:
- Strips YAML Front Matter
- Applies the "default" theme (clean, modern styling with green accents)
- Preserves `{{CONTENT_IMAGE_N}}` placeholders for the publish step

## Step 4: Publish to Draft Box

### Prerequisites
Ensure `.wx_config.json` exists in the current working directory (see **Configuration** section above).
If missing, ask the user for AppID and AppSecret, then create the file.

### Publish command

```bash
python scripts/publish_to_wechat.py \
  --config .wx_config.json \
  --html article.html \
  --title "文章标题" \
  --author "作者名" \
  --digest "文章摘要" \
  --cover cover.png \
  --content-images content_1.png content_2.png
```

The script will:
1. Obtain/refresh the WeChat access token
2. Upload cover image as permanent material → get `media_id`
3. Upload content images as article images → get CDN URLs
4. Replace `{{CONTENT_IMAGE_N}}` placeholders in HTML with CDN URLs
5. Call the draft creation API
6. Return the draft `media_id`

### Error handling
- If token errors (40001): delete `.wx_token_cache.json` and retry
- If upload errors (40004): check image format (PNG/JPEG/GIF, ≤10MB)
- If content too long (45008): reduce article length
- See `references/wechat_api.md` for full error code reference

## Partial Workflows

Users may request only part of the pipeline. Support these independently:

- **"帮我写一篇公众号文章"** → Steps 1-2 only, output Markdown + images
- **"帮我排版这篇文章"** → Step 3 only, convert existing Markdown to HTML
- **"帮我发布到草稿箱"** → Step 4 only, publish existing HTML + images
- **"帮我生成公众号配图"** → Step 2 only, generate images based on description

## Resources

- `scripts/publish_to_wechat.py` — WeChat API client (token, upload, draft creation)
- `scripts/generate_images.py` — Multi-provider AI image generator (OpenAI / Stability AI / fallback)
- `scripts/md_to_html.py` — Markdown to inline-styled HTML converter
- `references/wechat_api.md` — WeChat MP API endpoints and error codes
- `references/article_styles.md` — Writing style definitions and Front Matter template
