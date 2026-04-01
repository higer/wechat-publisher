#!/usr/bin/env python3
"""
Convert Markdown to WeChat MP-compatible inline-styled HTML.

Usage:
    python md_to_html.py input.md -o output.html [--theme default]

The output HTML uses inline CSS only (no <style> blocks) for WeChat compatibility.
Content images use placeholder URLs like {{CONTENT_IMAGE_1}} that get replaced
during the publish step.
"""

import argparse
import re
import html as html_module
import sys


# --- Theme Definitions (inline CSS) ---

THEMES = {
    "default": {
        "body": "margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:16px;line-height:1.8;color:#333;",
        "h1": "font-size:24px;font-weight:700;color:#1a1a1a;margin:28px 0 16px 0;padding-bottom:10px;border-bottom:2px solid #f0f0f0;",
        "h2": "font-size:20px;font-weight:700;color:#1a1a1a;margin:24px 0 12px 0;padding-left:10px;border-left:4px solid #07c160;",
        "h3": "font-size:18px;font-weight:600;color:#333;margin:20px 0 10px 0;",
        "p": "margin:12px 0;text-align:justify;",
        "blockquote": "margin:16px 0;padding:12px 16px;background:#f7f7f7;border-left:4px solid #ddd;color:#666;font-size:15px;",
        "img": "max-width:100%;height:auto;border-radius:6px;margin:16px auto;display:block;",
        "ul": "margin:12px 0;padding-left:24px;",
        "ol": "margin:12px 0;padding-left:24px;",
        "li": "margin:4px 0;",
        "strong": "font-weight:700;color:#1a1a1a;",
        "em": "font-style:italic;color:#555;",
        "code": "background:#f5f5f5;padding:2px 6px;border-radius:3px;font-size:14px;font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;color:#e96900;",
        "pre": "background:#f5f5f5;padding:16px;border-radius:6px;overflow-x:auto;font-size:14px;line-height:1.6;",
        "hr": "border:none;border-top:1px solid #e8e8e8;margin:24px 0;",
        "a": "color:#07c160;text-decoration:none;",
        "figcaption": "text-align:center;font-size:13px;color:#999;margin-top:6px;",
        "section": "padding:16px;",
    },
}


def get_style(theme: str, tag: str) -> str:
    t = THEMES.get(theme, THEMES["default"])
    return t.get(tag, "")


# --- Markdown Parser (lightweight, no external deps) ---

def parse_markdown_to_html(md_text: str, theme: str = "default") -> str:
    """Convert markdown text to inline-styled HTML for WeChat."""
    lines = md_text.split("\n")
    html_parts = []
    in_code_block = False
    code_buffer = []
    in_list = None  # 'ul' or 'ol'
    list_buffer = []

    def flush_list():
        nonlocal in_list, list_buffer
        if in_list and list_buffer:
            tag = in_list
            items = "".join(
                f'<li style="{get_style(theme, "li")}">{item}</li>'
                for item in list_buffer
            )
            html_parts.append(f'<{tag} style="{get_style(theme, tag)}">{items}</{tag}>')
            list_buffer = []
            in_list = None

    def inline_format(text: str) -> str:
        """Handle inline markdown: bold, italic, code, links, images."""
        # Images: ![alt](url)
        text = re.sub(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            lambda m: (
                f'<img src="{m.group(2)}" alt="{m.group(1)}" style="{get_style(theme, "img")}" />'
                + (f'<p style="{get_style(theme, "figcaption")}">{m.group(1)}</p>' if m.group(1) else "")
            ),
            text,
        )
        # Links: [text](url)
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            lambda m: f'<a href="{m.group(2)}" style="{get_style(theme, "a")}">{m.group(1)}</a>',
            text,
        )
        # Bold: **text**
        text = re.sub(
            r"\*\*(.+?)\*\*",
            lambda m: f'<strong style="{get_style(theme, "strong")}">{m.group(1)}</strong>',
            text,
        )
        # Italic: *text*
        text = re.sub(
            r"\*(.+?)\*",
            lambda m: f'<em style="{get_style(theme, "em")}">{m.group(1)}</em>',
            text,
        )
        # Inline code: `code`
        text = re.sub(
            r"`([^`]+)`",
            lambda m: f'<code style="{get_style(theme, "code")}">{html_module.escape(m.group(1))}</code>',
            text,
        )
        return text

    for line in lines:
        # Code block
        if line.strip().startswith("```"):
            if in_code_block:
                code_content = html_module.escape("\n".join(code_buffer))
                html_parts.append(
                    f'<pre style="{get_style(theme, "pre")}"><code>{code_content}</code></pre>'
                )
                code_buffer = []
                in_code_block = False
            else:
                flush_list()
                in_code_block = True
            continue
        if in_code_block:
            code_buffer.append(line)
            continue

        stripped = line.strip()

        # Empty line
        if not stripped:
            flush_list()
            continue

        # Headings
        h_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if h_match:
            flush_list()
            level = len(h_match.group(1))
            tag = f"h{level}"
            content = inline_format(h_match.group(2))
            html_parts.append(f'<{tag} style="{get_style(theme, tag)}">{content}</{tag}>')
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}$", stripped):
            flush_list()
            html_parts.append(f'<hr style="{get_style(theme, "hr")}" />')
            continue

        # Blockquote
        if stripped.startswith(">"):
            flush_list()
            content = inline_format(stripped.lstrip("> ").strip())
            html_parts.append(
                f'<blockquote style="{get_style(theme, "blockquote")}">{content}</blockquote>'
            )
            continue

        # Unordered list
        ul_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        if ul_match:
            if in_list != "ul":
                flush_list()
                in_list = "ul"
            list_buffer.append(inline_format(ul_match.group(1)))
            continue

        # Ordered list
        ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ol_match:
            if in_list != "ol":
                flush_list()
                in_list = "ol"
            list_buffer.append(inline_format(ol_match.group(1)))
            continue

        # Paragraph
        flush_list()
        content = inline_format(stripped)
        html_parts.append(f'<p style="{get_style(theme, "p")}">{content}</p>')

    flush_list()

    body = "\n".join(html_parts)
    return f'<section style="{get_style(theme, "section")}">\n{body}\n</section>'


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to WeChat HTML")
    parser.add_argument("input", help="Path to Markdown file")
    parser.add_argument("-o", "--output", required=True, help="Path to output HTML file")
    parser.add_argument("--theme", default="default", choices=list(THEMES.keys()), help="Theme name")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Strip YAML frontmatter if present
    if md_text.startswith("---"):
        end = md_text.find("---", 3)
        if end != -1:
            md_text = md_text[end + 3:].strip()

    html_output = parse_markdown_to_html(md_text, theme=args.theme)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"[OK] HTML written to {args.output}")


if __name__ == "__main__":
    main()
