#!/usr/bin/env python3
"""Batch generate comic story panels via GPT Image 2.

配方驱动版：画风 prompt 从 STYLES.md 读取，自动填充【主体】【光影】【画纸】占位符
（以及 doodle 配方的【文字】占位符），禁止手工缩写。支持连续分镜的画风一致性
（style-anchor 参考图机制）。colored-pencil 彩铅配方不含【文字】，生图不画文字只留白，旁白后期手动添加。

抗同质化变量机制（V2，仅 colored-pencil 生效）：
  - STYLES.md 内置「光影氛围库」「画纸纹理库」共 6+5 套变量。
  - story JSON 可用 lighting / paper 字段指定（1-6 / 1-5 序号，或直接写描述文本）；
    未指定时脚本自动轮换：同一篇内锁定一套，跨篇记入 skill 根目录 USAGE.json，
    尽量不重复最近用过的组合，规避平台 AI 批量生图判定。

Usage:
  python3 generate_story.py --story-json story.json --output-dir /var/minis/attachments
  python3 generate_story.py --story-json story.json --style colored-pencil
  python3 generate_story.py --story-json story2.json --lighting 3 --paper 5
  python3 generate_story.py --story-json story8.json --style colored-pencil --split2

Split2 双分镜模式（仅 colored-pencil）：
  - 总格数 >6 时启用；第1格作封面单图（竖版3:4），其余相邻两格拼成一张
    1024x1536 双分镜图，中间用极淡浅灰细线（#d9d9d9）分隔，禁止粗黑漫画边框。
  - 每个分镜上方预留干净留白区，生图不画文字，旁白后期手动添加；同一张图内上下两分镜
    光影色调统一；分镜构图均衡不拥挤、彩铅细节完整、不压缩笔触质感。
  - 封面必为单图，不能一图两格。
  - 开启方式：CLI `--split2` 或 story JSON `"split2": true`；≤6格自动回退逐格单图。

Story JSON format:
{
  "title": "等",
  "style": "colored-pencil",
  "anchor": "optional/path/anchor.png",   # 可选：画风锚点图，每格都传以保证多格一致
  "lighting": 3,                          # 可选：光影序号 1-6；不填则自动轮换
  "paper": 2,                             # 可选：画纸序号 1-5；不填则自动轮换
  "split2": true,                         # 可选：双分镜模式（总格数>6才真正生效）
  "panels": [
    {
      "id": "p1",
      "scene": "A girl sitting on a chair hugging knees...",   # 画面描述（英文）
      "text": "等一个人。"   # 彩铅：不画进图（仅供情绪推断/剧情记录），生图只留白后期自加字；涂鸦：画进图里的中文
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
from io import BytesIO


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
                   anchor_path: str | None = None,
                   size: str = "1024x1536") -> bytes:
    """生成单格图片，返回 JPEG 原始字节。

    若提供 anchor_path（画风锚点图），把上一格的输出作为 Image 1、锚点作为 Image 2，
    用图生图方式生成，锁定多格画风一致性（借鉴 hand-drawn-styles 的锚点机制）。
    size：单图输出尺寸。竖版条漫默认 1024x1536；双分镜模式下单格单元用 1024x1024。
    """
    prompt = style_prompt + "\n\nSCENE: " + scene

    # 构造请求体：文生图 或 图生图（带锚点参考）
    body: dict = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "size": size,
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


def compose_split2(top_bytes: bytes, bottom_bytes: bytes,
                   target_w: int = 1024, target_h: int = 1536,
                   seam: int = 8, separator_color=(217, 217, 217)) -> bytes:
    """把上下两个分镜单元竖直拼接成一张 3:4 竖版双分镜图。

    中间保留一条 seam 像素高的"极淡浅灰色细线"作分镜分隔（默认 #d9d9d9，远非黑色粗线）。
    两个单元先各自条缩到统一宽度再拼接，以保留彩铅笔触细节、避免过度压缩画质。
    返回 JPEG 字节。
    """
    from PIL import Image, ImageDraw
    top = Image.open(BytesIO(top_bytes)).convert("RGB")
    bottom = Image.open(BytesIO(bottom_bytes)).convert("RGB")

    # 两单元统一高（目标高度扣除分隔线后，上下各半）
    body_h = target_h - seam
    unit_h = body_h // 2

    def _fit(img, w, h):
        # 覆盖裁剪：保证铺满目标区域，优先保留画面主体（居中）
        img.thumbnail((w * 2, h * 2), Image.LANCZOS)
        ow, oh = img.size
        scale = max(w / ow, h / oh)
        img = img.resize((int(ow * scale), int(oh * scale)), Image.LANCZOS)
        img = img.crop(((img.width - w) // 2, (img.height - h) // 2,
                        (img.width + w) // 2, (img.height + h) // 2))
        return img

    top = _fit(top, target_w, unit_h)
    bottom = _fit(bottom, target_w, unit_h)

    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    canvas.paste(top, (0, 0))
    canvas.paste(bottom, (0, unit_h + seam))

    draw = ImageDraw.Draw(canvas)
    draw.line([(0, unit_h + seam // 2), (target_w, unit_h + seam // 2)],
              fill=separator_color, width=seam)
    # 极淡浅灰细线，近似画纸折痕，非漫画粗黑边框

    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


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
    ap.add_argument("--split2", action="store_true",
        help="双分镜模式（仅 colored-pencil）：总格数>6 时，第1格作封面单图（竖版3:4），"
             "其余相邻两格拼成一张 1024x1536 双分镜图，中间用极淡浅灰色细线分隔。"
             "也可在 story JSON 里用 \"split2\": true 开启。",
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

    # ---- 双分镜模式判定 ----
    # 规则：仅 colored-pencil；总格数 >6 才启用；第1格作为封面单图（竖版3:4），
    # 其余相邻两格拼成一张 1024x1536 双分镜图（中间极淡浅灰细线分隔）。
    split2 = (args.split2 or bool(story.get("split2", False))) and style == "colored-pencil"
    if split2:
        split2 = len(panels) > 6
        if args.split2 and len(panels) <= 6:
            print("⚠️  split2 已开启但总格数≤6，回退为逐格单图。")
    print(f"Split2(双分镜): {'ON' if split2 else 'OFF'}")
    print()

    # 生成清单：每项 (index, panel)。封面(index 0)单独处理，其余按双分镜分组。
    # 分组：(1,2)(3,4)(5,6)...；若最后一组只有一格，则该格单独成图。
    jobs = []
    if split2:
        jobs.append({"type": "cover", "idx": 0, "panel": panels[0]})
        i = 1
        while i < len(panels):
            top = {"idx": i, "panel": panels[i]}
            if i + 1 < len(panels):
                jobs.append({"type": "double", "idx": i,
                             "top": top, "bottom": {"idx": i + 1, "panel": panels[i + 1]}})
                i += 2
            else:
                jobs.append({"type": "single", "idx": i, "panel": panels[i]})
                i += 1
    else:
        jobs = [{"type": "single", "idx": i, "panel": panels[i]} for i in range(len(panels))]

    def _render_prompt(panel, framing: str = "vertical") -> str | None:
        scene = panel["scene"]
        fill = {"主体": scene, **var_values}
        # 仅当配方含【文字】占位符才填充文字（doodle 涂鸦画字进图）；
        # colored-pencil 彩铅配方已不含【文字】，生图只留白、不画字。
        phs = set(PLACEHOLDER_PATTERN.findall(style_template))
        if "文字" in phs:
            fill["文字"] = panel.get("text", "")
        if "构图" in phs:
            if framing == "square":
                fill["构图"] = (
                    "This image is ONE upper/lower half-panel of a two-panel vertical stack. "
                    "Square canvas. The top quarter of this panel is clean blank whitespace reserved "
                    "for a narration sentence that will be added later; leave it COMPLETELY EMPTY, "
                    "do NOT draw any text, character, letter or watermark in it. "
                    "The subject occupies the lower three-quarters, drawn centered with balanced, "
                    "uncrowded composition and generous negative space."
                )
            else:
                fill["构图"] = (
                    "Single vertical 3:4 canvas showing ONE narrative panel filling the whole image. "
                    "The top portion of the canvas is a clean blank band reserved for a narration "
                    "sentence that will be added later; leave it COMPLETELY EMPTY, do NOT draw any "
                    "text, character, letter or watermark in it. "
                    "The subject is placed centered in the lower portion with balanced, "
                    "uncrowded composition and generous negative space."
                )
        if "分镜结构" in phs:
            if framing == "square":
                fill["分镜结构"] = (
                    "This half-panel will be stacked with another, so keep its internal framing "
                    "self-contained: subject not spilling toward the shared edge, a soft sheet-light "
                    "separating the two panels, lighting and palette matched across both halves."
                )
            else:
                fill["分镜结构"] = (
                    "Cover/standalone image: full single frame, subject well inside the frame, "
                    "no internal division, the whole canvas is one narrative panel."
                )
        try:
            return render(style_template, fill)
        except ValueError as e:
            print(f"  render error: {e}", file=sys.stderr)
            return None

    def _anchor_for(idx: int) -> str | None:
        if anchor_path:
            return anchor_path
        prev_path = os.path.join(args.output_dir, f"story_{panels[idx-1]['id']}.jpeg")
        if idx > 0 and os.path.isfile(prev_path):
            return prev_path
        return None

    def _generate_unit(job, out_key) -> str | None:
        """生成一个分镜单元，返回保存路径；失败返回 None。"""
        idx = job["idx"]
        panel = job["panel"]
        pid = panel["id"]
        scene = panel["scene"]
        size = "1024x1024" if job.get("unit_size") == "square" else "1024x1536"
        out_path = job.get("out_path") or os.path.join(args.output_dir, f"story_{pid}.jpeg")

        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print(f"[{out_key}] {pid}: already exists, using existing")
            return out_path

        style_prompt = _render_prompt(panel, framing=("square" if job.get("unit_size") == "square" else "vertical"))
        if style_prompt is None:
            return None

        print(f"[{out_key}] {pid}: generating ({size})...")
        sys.stdout.flush()
        t0 = time.time()
        try:
            img_bytes = generate_panel(scene, style_prompt, api_url, api_key,
                                       _anchor_for(idx), size=size)
            with open(out_path, "wb") as f:
                f.write(img_bytes)
            elapsed = time.time() - t0
            print(f"  ✅ {out_path} ({len(img_bytes)//1024}KB, {elapsed:.1f}s)")
            return out_path
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ❌ failed ({elapsed:.1f}s): {e}")
            return None

    # 若已存在拼好的双分镜图，跳过整组（用于断点续跑）
    composed_paths = []

    for job in jobs:
        if job["type"] == "cover":
            # 封面必为单图（竖版3:4），不参与双分镜拼接
            job["unit_size"] = "vertical"
            _generate_unit(job, f"cover {job['idx']+1}")
        elif job["type"] == "single":
            job["unit_size"] = "vertical"
            _generate_unit(job, f"single {job['idx']+1}")
        elif job["type"] == "double":
            top_idx = job["top"]["idx"]
            bottom_idx = job["bottom"]["idx"]
            top_pid = job["top"]["panel"]["id"]
            bottom_pid = job["bottom"]["panel"]["id"]
            composed = os.path.join(args.output_dir, f"story_split_{top_idx+1}_{bottom_idx+1}.jpeg")
            if os.path.exists(composed) and os.path.getsize(composed) > 10000:
                print(f"[double {top_idx+1}~{bottom_idx+1}]: already composed, using existing")
                composed_paths.append(composed)
                top_path = os.path.join(args.output_dir, f"story_{top_pid}.jpeg")
                bottom_path = os.path.join(args.output_dir, f"story_{bottom_pid}.jpeg")
                still_ok = (os.path.exists(top_path) and os.path.getsize(top_path) > 10000 and
                            os.path.exists(bottom_path) and os.path.getsize(bottom_path) > 10000)
                if not still_ok:
                    continue
                print(f"  ✅ {composed}")
                continue

            # 生成上下两个分镜单元（方形，以留足像素、减少拼图压缩损失）
            top_job = {"idx": top_idx, "panel": job["top"]["panel"], "unit_size": "square"}
            bottom_job = {"idx": bottom_idx, "panel": job["bottom"]["panel"], "unit_size": "square"}
            top_path = _generate_unit(top_job, f"top {top_idx+1}")
            bottom_path = _generate_unit(bottom_job, f"bottom {bottom_idx+1}")
            if not top_path or not bottom_path:
                print(f"⚠️  [double {top_idx+1}~{bottom_idx+1}]: 上下分镜未全部生成，跳过拼接")
                continue

            # 拼接：极淡浅灰细线分隔，竖版 3:4
            try:
                with open(top_path, "rb") as f:
                    top_bytes = f.read()
                with open(bottom_path, "rb") as f:
                    bottom_bytes = f.read()
                merged = compose_split2(top_bytes, bottom_bytes)
                with open(composed, "wb") as f:
                    f.write(merged)
                composed_paths.append(composed)
                print(f"  ✅ {composed} ({len(merged)//1024}KB, 双分镜拼接完成)")
            except Exception as e:
                print(f"  ❌ [double {top_idx+1}~{bottom_idx+1}] 拼接失败: {e}")
        sys.stdout.flush()

    print("\nDone! All panels saved to:", args.output_dir)
    if composed_paths:
        print("双分镜图：")
        for p in composed_paths:
            print(f"  - {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
