#!/usr/bin/env python3
"""Batch generate comic story panels via GPT Image 2.

配方驱动版：画风 prompt 从 STYLES.md 读取，自动填充【主体】【文字】【光影】【画纸】占位符，
禁止手工缩写。支持连续分镜的画风一致性（style-anchor 参考图机制）。

抗同质化变量机制（V2，仅 colored-pencil 生效）：
  - STYLES.md 内置「光影氛围库」「画纸纹理库」共 6+5 套变量。
  - story JSON 可用 lighting / paper 字段指定（1-6 / 1-5 序号，或直接写描述文本）；
    未指定时脚本自动轮换：同一篇内锁定一套，跨篇记入 skill 根目录 USAGE.json，
    尽量不重复最近用过的组合，规避平台 AI 批量生图判定。

Usage:
  python3 generate_story.py --story-json story.json --output-dir /var/minis/attachments
  python3 generate_story.py --story-json story.json --style colored-pencil
  python3 generate_story.py --story-json story2.json --lighting 3 --paper 5

Story JSON format:
{
  "title": "等",
  "style": "colored-pencil",
  "anchor": "optional/path/anchor.png",   # 可选：画风锚点图，每格都传以保证多格一致
  "lighting": 3,                          # 可选：光影序号 1-6；不填则自动轮换
  "paper": 2,                             # 可选：画纸序号 1-5；不填则自动轮换
  "panels": [
    {
      "id": "p1",
      "scene": "A girl sitting on a chair hugging knees...",   # 画面描述（英文）
      "text": "旁白：等一个人。对话：你在哪？"                  # 画进图里的中文（必填）
    }
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
USAGE_PATH = os.path.join(ROOT, "USAGE.json")  # 抗同质化变量使用记录
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
    """列出 STYLES.md 中所有可用画风编号/名称（排除变量库标题）。"""
    with open(STYLES_PATH, encoding="utf-8") as f:
        source = f.read()
    titles = re.findall(r"^## (\S+)", source, re.MULTILINE)
    return [t for t in titles if "变量库" not in t]


def extract_library(lib_name: str) -> list[str]:
    """从 STYLES.md 提取「光影氛围变量库」/「画纸纹理变量库」代码块。

    返回条目列表，每项已去掉行首的 'N. ' 序号前缀。
    """
    with open(STYLES_PATH, encoding="utf-8") as f:
        source = f.read()
    heading = re.compile(
        r"^## " + re.escape(lib_name) + r"(?:[^\n]*)\n.*?^```[^\n]*\n(.*?)^```",
        re.MULTILINE | re.DOTALL,
    )
    match = heading.search(source)
    if not match:
        raise ValueError(f"STYLES.md 中不存在变量库 '{lib_name}'。")
    items = []
    for line in match.group(1).strip().splitlines():
        line = line.strip()
        if not line:
            continue
        item = re.sub(r"^\d+[\.、]\s*", "", line)
        items.append(item)
    return items


def pick_variant(seq_arg, unused_lists, lib_items, field_name, usage_key):
    """选择一个变量。

    seq_arg: story JSON 或 CLI 传入的序号（int/str）+1 处理 / 描述文本 / None。
    返回 (选中描述, 序号或 None)。
    优先用指定；未指定则从未用池里轮换一个；池空则循环。
    """
    # 1) 显式指定
    if seq_arg is not None:
        if isinstance(seq_arg, str):
            seq_arg = seq_arg.strip()
            # 支持传描述文本
            for it in lib_items:
                if it == seq_arg or seq_arg in it:
                    return it, lib_items.index(it) + 1
            # 支持传带序号的字符串 "3" / "L3" / "光影3"
            m = re.search(r"(\d+)", seq_arg)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(lib_items):
                    return lib_items[idx], idx + 1
                raise ValueError(f"{field_name} 序号越界: {seq_arg} (可用 1-{len(lib_items)})")
            raise ValueError(f"无法解析 {field_name} 参数: {seq_arg}")
        if isinstance(seq_arg, int):
            idx = seq_arg - 1
            if 0 <= idx < len(lib_items):
                return lib_items[idx], seq_arg
            raise ValueError(f"{field_name} 序号越界: {seq_arg} (可用 1-{len(lib_items)})")
        raise ValueError(f"{field_name} 参数类型无效: {type(seq_arg)}")

    # 2) 未指定 → 轮换：从未用池里挑
    unused = unused_lists.get(usage_key, [])
    if not unused:
        # 池空则重置为全量（跨篇已全部用过一轮，重新开始）
        unused = list(range(1, len(lib_items) + 1))
    idx = unused.pop(0)
    unused_lists[usage_key] = unused
    return lib_items[idx - 1], idx


def infer_lighting(all_texts: str) -> int | None:
    """从故事文本推断最匹配的光影序号（1-6），推断不出返回 None。

    按"渐进覆盖优先级"匹配：情绪/情景词从日常→释怀→扎心→怀旧→清醒 递进，
    后命中的更强烈的情绪覆盖前面的（如"扎心"覆盖"温馨"）。
    对应 STYLES.md「光影氛围库」的 6 套定位。
    """
    # (优先级, 光影序号, [触发词])
    # 优先级：数字越大越靠后判定、越强，命中即覆盖低优先级
    rules = [
        # 6 室内顶光：清醒、释然、通透
        (6, 6, ["释然", "清醒", "放下", "想通了", "悟了", "看开了", "终于明白", "明白了", "豁然开朗", "走出来", "释怀"]),
        # 5 黄昏暖调：怀旧、多年回望
        (5, 5, ["多年", "许多年", "多年后", "回望", "往昔", "那些年", "小时候", "老照片", "泛黄", "旧时光", "再见到", "重逢"]),
        # 4 局部硬光：误会、紧张、扎心、转折
        (4, 4, ["误会", "争吵", "扎心", "背叛", "欺骗", "真相", "转折", "反转", "狠心", "决裂", "心碎", "泪", "眼泪", "哭", "一巴掌", "擦肩"]),
        # 3 弱冷调柔光：释怀、emo、反转结局（弱于4）
        (3, 3, ["算了吧", "就这样", "深夜", "emo", "沉默", "失眠", "发呆", "空了", "落空", "酸涩", "空欢喜", "一厢情愿"]),
        # 2 窗边侧逆光：回忆、暗恋、遗憾
        (2, 2, ["回忆", "想起", "记得", "从前", "暗恋", "遗憾", "错过", "可惜", "没来得及", "如果", "要是"]),
        # 1 柔和正面光：日常温馨
        (1, 1, ["温馨", "日常", "平凡", "早上", "傍晚", "买菜", "做饭", "吃饭", "回家", "一起", "陪伴", "温暖", "阳光"]),
    ]
    best = 0
    best_no = None
    for pri, no, words in rules:
        for w in words:
            if w in all_texts:
                if pri >= best:
                    best = pri
                    best_no = no
                break
    return best_no


def load_usage() -> dict:
    if os.path.isfile(USAGE_PATH):
        try:
            with open(USAGE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_usage(usage: dict) -> None:
    try:
        with open(USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(usage, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


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
        description="Generate comic story panels (recipe-driven, supports style-anchor and anti-homogenization variants)"
    )
    ap.add_argument("--story-json", default=None, help="Path to story JSON file")
    ap.add_argument("--output-dir", default="/var/minis/attachments", help="Output directory")
    ap.add_argument(
        "--style",
        default=None,
        help="Style override (default: read from story JSON or 'doodle'). "
             "Available styles are listed with --list-styles.",
    )
    ap.add_argument(
        "--lighting", default=None, type=str,
        help="Optional lighting variant: index (1-6) or description text. Anti-homogenization.",
    )
    ap.add_argument(
        "--paper", default=None, type=str,
        help="Optional paper-texture variant: index (1-5) or description text. Anti-homogenization.",
    )
    ap.add_argument("--list-styles", action="store_true", help="List available styles and exit")
    ap.add_argument("--list-variants", action="store_true", help="List lighting/paper variant libraries and exit")
    args = ap.parse_args()

    if args.list_styles:
        print("Available styles in STYLES.md:")
        for s in list_styles():
            print(f"  - {s}")
        return 0

    if args.list_variants:
        try:
            print("光影氛围库:")
            for i, it in enumerate(extract_library("光影氛围变量库"), 1):
                print(f"  {i}. {it}")
            print("\n画纸纹理库:")
            for i, it in enumerate(extract_library("画纸纹理变量库"), 1):
                print(f"  {i}. {it}")
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
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

    # ---- 抗同质化变量机制（仅对含【光影】【画纸】占位符的配方生效）----
    var_values = {}
    lighting_seq = args.lighting if args.lighting is not None else story.get("lighting")
    paper_seq = args.paper if args.paper is not None else story.get("paper")
    if "光影" in set(PLACEHOLDER_PATTERN.findall(style_template)):
        usage = load_usage()
        unused = usage.setdefault("unused", {"lighting": [], "paper": []})
        lib_l = extract_library("光影氛围变量库")
        lib_p = extract_library("画纸纹理变量库")

        # 收集故事全文（title + 每格 scene + text），用于情绪推断
        all_texts = " ".join(
            f"{p.get('scene','')} {p.get('text','')}" for p in panels
        ) + " " + str(story.get("title", ""))

        # ---- 光影：手动指定 > 情绪自动推断 > 自动轮换 ----
        if lighting_seq is None:
            inferred = infer_lighting(all_texts)
            if inferred is not None:
                lit_desc, lit_idx = lib_l[inferred - 1], inferred
                u = unused.get("lighting", [])
                if inferred in u:
                    u.remove(inferred)  # 从未用池剔除，避免后续轮换撞
                print(f"[变量] 光影#{lit_idx}（情绪自动推断）: {lit_desc}")
            else:
                lit_desc, lit_idx = pick_variant(None, unused, lib_l, "lighting", "lighting")
                print(f"[变量] 光影#{lit_idx}（自动轮换）: {lit_desc}")
        else:
            lit_desc, lit_idx = pick_variant(lighting_seq, unused, lib_l, "lighting", "lighting")
            print(f"[变量] 光影#{lit_idx}（手动指定）: {lit_desc}")

        # ---- 画纸：手动指定 > 自动轮换（画纸与情绪弱相关，直接轮换）----
        pap_desc, pap_idx = pick_variant(paper_seq, unused, lib_p, "paper", "paper")
        print(f"[变量] 画纸#{pap_idx}: {pap_desc}")

        var_values = {
            "光影": lit_desc,
            "画纸": pap_desc,
        }
        # 记录使用，供数据复盘表参考
        usage["history"] = usage.get("history", [])
        usage["history"].append({
            "title": story.get("title", "untitled"),
            "style": style,
            "lighting": lit_idx,
            "paper": pap_idx,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        save_usage(usage)

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
        # 【主体】= 画面场景描述，【文字】= 画进图里的中文（对话+旁白）
        text = panel.get("text", "")
        fill = {"主体": scene, "文字": text, **var_values}
        try:
            style_prompt = render(style_template, fill)
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
