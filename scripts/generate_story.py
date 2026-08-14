#!/usr/bin/env python3
"""Batch generate comic story panels via GPT Image 2.

配方驱动版：画风 prompt 从 STYLES.md 读取，自动填充【主体】占位符，
禁止手工缩写。支持连续分镜的画风一致性（style-anchor 参考图机制）。

Usage:
  python3 generate_story.py --story-json story.json --output-dir /var/minis/attachments
  python3 generate_story.py --story-json story.json --style colored-pencil

Story JSON format:
{
  "title": "等",
  "style": "doodle",
  "anchor": "optional/path/anchor.png",   # 可选：画风锚点图，每格都传以保证多格一致
  "panels": [
    {"id": "p1", "scene": "A girl sitting on a chair hugging knees..."},
    {"id": "p2", "scene": "Same pose, calendar page flipped, sky dimmer."}
  ]
}

Environment variables:
  IMAGE_API_URL   - Image generation API base URL (e.g. https://host/v1)
  OPENAI_API_KEY  - API key for authentication
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # skill 根目录
STYLES_PATH = os.path.join(ROOT, "STYLES.md")
PLACEHOLDER_PATTERN = re.compile(r"【([^】]+)】")


def extract_template(style_id: str) -> str:
    """从 STYLES.md 原样提取指定画风的代码块配方，不缩写不改动。"""
    with open(STYLES_PATH, encoding="utf-8") as f:
        source = f.read()
    heading = re.compile(
        r"^## " + re.escape(style_id) + r"(?:[^\n]*)\n.*?^```[^\n]*\n(.*?)^```",
        re.MULTILINE | re.DOTALL,
    )
    match = heading.search(source)
    if not match:
        raise ValueError(
            f"STYLES.md 中不存在画风 '{style_id}' 的代码块配方。"
            f"可用画风见 STYLES.md 的 ## 标题。"
        )
    return match.group(1).strip()


def list_styles() -> list[str]:
    """列出 STYLES.md 中所有可用画风编号/名称。"""
    with open(STYLES_PATH, encoding="utf-8") as f:
        source = f.read()
    return re.findall(r"^## (\S+)", source, re.MULTILINE)


def render(template: str, values: dict[str, str]) -> str:
    """填充占位符并校验：缺占位符报错、未知占位符报错、残留占位符报错。"""
    expected = set(PLACEHOLDER_PATTERN.findall(template))
    unknown = sorted(set(values) - expected)
    if unknown:
        raise ValueError(f"配方不包含这些占位符: {', '.join(unknown)}")
    missing = sorted(expected - set(values))
    if missing:
        raise ValueError(f"缺少占位符: {', '.join(missing)}")
    output = template
    for key, value in values.items():
        output = output.replace(f"【{key}】", value)
    unresolved = sorted(set(PLACEHOLDER_PATTERN.findall(output)))
    if unresolved:
        raise ValueError(f"仍有未替换占位符: {', '.join(unresolved)}")
    return output


def generate_panel(scene: str, style_prompt: str, api_url: str, api_key: str,
                   anchor_path: str | None = None) -> bytes:
    """生成单格图片，返回 JPEG 原始字节。

    若提供 anchor_path（画风锚点图），把上一格的输出作为 Image 1、锚点作为 Image 2，
    用图生图方式生成，锁定多格画风一致性（借鉴 hand-drawn-styles 的锚点机制）。
    """
    prompt = style_prompt + "\n\nSCENE: " + scene

    # 构造请求体：文生图 或 图生图（带锚点参考）
    body: dict = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "size": "1024x1536",
        "quality": "high",
        "n": 1,
    }

    if anchor_path and os.path.isfile(anchor_path):
        with open(anchor_path, "rb") as f:
            anchor_b64 = base64.b64encode(f.read()).decode()
        body["image"] = f"data:image/png;base64,{anchor_b64}"
        body["prompt"] = (
            "Image 1 is the approved style-only reference. "
            "Match its line weight, coloring, character proportions, mood and palette. "
            "Do NOT copy the people, clothing, positions or story from Image 1 — only inherit the visual style. "
            + prompt
        )

    payload = json.dumps(body).encode()

    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/images/generations",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())

    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")
    b64 = data["data"][0]["b64_json"]
    return base64.b64decode(b64)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate comic story panels (recipe-driven, supports style-anchor for consistency)"
    )
    ap.add_argument("--story-json", default=None, help="Path to story JSON file")
    ap.add_argument("--output-dir", default="/var/minis/attachments", help="Output directory")
    ap.add_argument(
        "--style",
        default=None,
        help="Style override (default: read from story JSON or 'doodle'). "
             "Available styles are listed with --list-styles.",
    )
    ap.add_argument("--list-styles", action="store_true", help="List available styles and exit")
    args = ap.parse_args()

    if args.list_styles:
        print("Available styles in STYLES.md:")
        for s in list_styles():
            print(f"  - {s}")
        return 0

    if not args.story_json:
        ap.error("the following arguments are required: --story-json")

    api_url = os.environ.get("IMAGE_API_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_url:
        print("ERROR: IMAGE_API_URL not set", file=sys.stderr)
        return 1
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 1

    story = json.load(open(args.story_json))
    panels = story["panels"]

    # 解析风格：CLI > JSON > 默认 doodle
    style = args.style or story.get("style", "doodle")
    try:
        style_template = extract_template(style)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Available styles:", ", ".join(list_styles()), file=sys.stderr)
        return 1

    # 画风锚点图（可选）：连续故事每格都传，锁多格画风一致
    anchor_path = story.get("anchor")

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Story: {story.get('title', 'untitled')} — {len(panels)} panels")
    print(f"Style: {style}")
    print(f"Anchor: {anchor_path or '(none)'}")
    print(f"Output: {args.output_dir}")
    print()

    for i, panel in enumerate(panels):
        pid = panel["id"]
        scene = panel["scene"]
        out_path = os.path.join(args.output_dir, f"story_{pid}.jpeg")

        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print(f"[{i+1}/{len(panels)}] {pid}: already exists, skipping")
            continue

        # 配方驱动：从模板填充占位符，禁止手改配方
        try:
            style_prompt = render(style_template, {"主体": scene})
        except ValueError as e:
            print(f"[{i+1}/{len(panels)}] {pid}: render error: {e}", file=sys.stderr)
            continue

        # 锚点机制：第 2 格起用上一格输出作为画风参考，锁连续一致性
        ref_anchor = None
        if anchor_path:
            ref_anchor = anchor_path
        elif i > 0:
            prev_path = os.path.join(args.output_dir, f"story_{panels[i-1]['id']}.jpeg")
            if os.path.isfile(prev_path):
                ref_anchor = prev_path

        print(f"[{i+1}/{len(panels)}] {pid}: generating...")
        sys.stdout.flush()
        t0 = time.time()
        try:
            img_bytes = generate_panel(scene, style_prompt, api_url, api_key, ref_anchor)
            with open(out_path, "wb") as f:
                f.write(img_bytes)
            elapsed = time.time() - t0
            print(f"  ✅ {out_path} ({len(img_bytes)//1024}KB, {elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ❌ failed ({elapsed:.1f}s): {e}")
        sys.stdout.flush()

    print("\nDone! All panels saved to:", args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
