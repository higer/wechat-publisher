# Article Style Guide

## Style Parameters

When generating articles, accept a `style` parameter. Supported styles and their writing guidance:

### tech (科技/互联网)
- Tone: professional, analytical, forward-looking
- Structure: phenomenon → analysis → insight → outlook
- Use data and case studies to support arguments
- Avoid jargon overload; explain technical concepts for a broad audience

### business (商业/财经)
- Tone: authoritative, data-driven, objective
- Structure: event/trend → background → multi-angle analysis → takeaway
- Include market data, company examples, industry comparisons
- Balance depth with readability

### lifestyle (生活/文化)
- Tone: warm, relatable, storytelling-driven
- Structure: hook → personal/relatable story → insight → call-to-action
- Use vivid descriptions and sensory details
- Connect everyday experiences to broader meaning

### education (教育/知识)
- Tone: clear, structured, encouraging
- Structure: question/problem → explanation → examples → summary
- Use analogies and step-by-step breakdowns
- Include actionable takeaways the reader can apply immediately

### opinion (观点/评论)
- Tone: sharp, persuasive, thought-provoking
- Structure: thesis → evidence → counterargument → conclusion
- Take a clear stance; avoid fence-sitting
- Use rhetorical techniques to engage the reader

## General Writing Rules (all styles)

1. Title: 15-30 characters, specific and attention-grabbing, avoid clickbait
2. Opening: hook within first 3 sentences — question, surprising fact, or bold statement
3. Paragraphs: 3-5 sentences each; use subheadings every 300-500 characters
4. Closing: end with insight, call-to-action, or thought-provoking question
5. Total length: 2000-4000 characters (Chinese), aim for 2500-3500 as default
6. Image placement: cover (before title), 1st content image (after ~30% of article), 2nd content image (after ~70% of article)

## Front Matter Template

```yaml
---
title: "文章标题"
author: "作者名"
date: "YYYY-MM-DD"
style: "tech|business|lifestyle|education|opinion"
digest: "120字以内的文章摘要"
tags:
  - tag1
  - tag2
cover: "cover.png"
content_images:
  - "content_1.png"
  - "content_2.png"
---
```
