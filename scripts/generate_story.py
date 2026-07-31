#!/usr/bin/env python3
"""Batch generate doodle comic story panels via GPT Image 2.

Usage:
  python3 generate_story.py --story-json story.json --output-dir /var/minis/attachments

Story JSON format:
{
  "title": "等",
  "panels": [
    {"id": "p1", "scene": "A girl sitting on a chair hugging knees..."},
    {"id": "p2", "scene": "Same pose, calendar flipped..."}
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
import sys
import time
import urllib.error
import urllib.request


STYLE_PROMPT = (
    "Hand-drawn doodle comic style illustration. "
    "Black and white rough ink line art on clean white background. "
    "The ONLY color in the image is ONE bright red element. "
    "Sketchy, trembling, casual ink lines with unfinished edges and spontaneous linework. "
    "Minimalist Q-version character: big head small body, simple dot eyes, messy tousled hair. "
    "Lots of white negative space, centered subject. "
    "Diary-style emotional illustration, melancholic yet humorous mood. "
    "No text, no speech bubbles, no words, no letters anywhere in the image."
)


def generate_panel(scene: str, api_url: str, api_key: str) -> bytes:
    """Generate a single panel image, return raw JPEG bytes."""
    prompt = STYLE_PROMPT + "\n\nSCENE: " + scene
    payload = json.dumps({
        "model": "gpt-image-2",
        "prompt": prompt,
        "size": "1024x1536",
        "quality": "high",
        "n": 1,
    }).encode()

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
    ap = argparse.ArgumentParser(description="Generate doodle comic story panels")
    ap.add_argument("--story-json", required=True, help="Path to story JSON file")
    ap.add_argument("--output-dir", default="/var/minis/attachments", help="Output directory")
    args = ap.parse_args()

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
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Story: {story.get('title', 'untitled')} — {len(panels)} panels")
    print(f"Output: {args.output_dir}")
    print()

    for i, panel in enumerate(panels):
        pid = panel["id"]
        scene = panel["scene"]
        out_path = os.path.join(args.output_dir, f"story_{pid}.jpeg")

        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print(f"[{i+1}/{len(panels)}] {pid}: already exists, skipping")
            continue

        print(f"[{i+1}/{len(panels)}] {pid}: generating...")
        sys.stdout.flush()
        t0 = time.time()
        try:
            img_bytes = generate_panel(scene, api_url, api_key)
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
