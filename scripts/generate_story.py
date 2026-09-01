#!/usr/bin/env python3
"""Batch generate comic story panels via GPT Image 2.

配方驱动版：画风 prompt 从 STYLES.md 读取，自动填充【主体】【光影】【画纸】占位符，
禁止手工缩写。支持连续分镜的画风一致性（style-anchor 参考图机制）。
**两风格生图均不画文字**：doodle 与 colored-pencil 配方都不含【文字】，顶部留白区完全空白，
旁白/台词由作者后期手动添加；story JSON 的 text 字段仅用于光影情绪推断与剧情记录。

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

Multipanel 整页多格模式（可选，与 split2 互斥）：
  - 仅 colored-pencil；需显式开启（CLI `--multipanel` 或 story JSON `"multipanel": true`）。
  - 总格数 ≥5 才启用；每页装 3-5 格，超 5 格自动拆多页；封面(首格)单独出单图。
  - 默认 free（自由艺术版，非等分+微旋转）；free 拼接多次失败自动降级 regular（规整节奏版）。
  - 指定风格：story JSON `"multipanel_style": "free|regular"` 或 CLI `--mp-style`。
  - 产物：story_page_<n>.jpeg（整页 1024x1536）+ story_<pid>.jpeg（分镜单元，供加字/审计）。

Story JSON format:
{
  "title": "等",
  "style": "colored-pencil",
  "anchor": "optional/path/anchor.png",   # 可选：画风锚点图，每格都传以保证多格一致
  "lighting": 3,                          # 可选：光影序号 1-6；不填则自动轮换
  "paper": 2,                             # 可选：画纸序号 1-5；不填则自动轮换
  "split2": true,                         # 可选：双分镜模式（总格数>6才真正生效，与 multipanel 互斥）
  "multipanel": false,                    # 可选：整页多格模式（总格数>=5才真正生效）
  "multipanel_style": "free",             # 可选：整页多格风格 free/regular
  "panels": [
    {
      "id": "p1",
      "scene": "A girl sitting on a chair hugging knees...",   # 画面描述（英文）
      "text": "等一个人。"   # 两风格均不画进图（仅供情绪推断/剧情记录），生图只留白，旁白后期手动添加
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

# 生图路线：无 IMAGE_API_URL 时回退 minis-model-use。
# 由 main 在启动时探测后置位（避免重复探测）。
_USE_MINI_MODEL = False

# 整页多格布局模板（仅 colored-pencil --multipanel 使用）
try:
    from multipanel_layouts import get_templates  # 与脚本同目录
except Exception:  # noqa: BLE001
    try:
        from baicat.scripts.multipanel_layouts import get_templates
    except Exception:  # noqa: BLE001
        get_templates = None


def _split_pages(n: int, min_p=3, max_p=5) -> list[int]:
    """把 n 个分镜切成若干页，每页 3-5 格，尽量贴近 4 格/页。"""
    if n <= 0:
        return []
    if n <= max_p:
        return [n]
    # 页数目标：每页 4 格（居中）
    pages_n = max(1, round(n / 4))
    base, rem = divmod(n, pages_n)
    sizes = [base + 1 if i < rem else base for i in range(pages_n)]
    # 修正：把 <min_p 的页合并/重分配
    while any(s < min_p for s in sizes):
        rebuilt = []
        carry = 0
        for s in sizes:
            s += carry
            if s >= max_p:
                rebuilt.append(max_p)
                carry = s - max_p
            elif len(rebuilt) < pages_n and s + 0 >= min_p and carry == 0:
                rebuilt.append(s)
                carry = 0
            else:
                rebuilt.append(min_p)
                carry = s - min_p
        sizes = rebuilt if sum(rebuilt) == n else sizes
        if all(min_p <= s <= max_p for s in sizes) and sum(sizes) == n:
            break
        # 兜底：暴力从 max_p 往下切
        sizes = []
        t = n
        while t > 0:
            take = min(max_p, t)
            if t - take == 1:  # 避免最后剩 1
                take -= 1
            if take < 1:
                take = 1
            sizes.append(take)
            t -= take
        break
    return sizes


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
    """生成单格图片，返回 JPEG/PNG 字节。

    路线：优先 IMAGE_API_URL 直调；`_USE_MINI_MODEL` 为 True 时改走
    `minis-model-use run --model gpt-image-2 --endpoint images-gen`。

    若提供 anchor_path（画风锚点图），作为 style-only 参考传入，锁定多格画风一致。
    size：1024x1536(竖版) 或 1024x1024(方形分镜单元)。
    """
    import subprocess
    use_local = _USE_MINI_MODEL
    prompt = style_prompt if not scene else style_prompt + "\n\nSCENE: " + scene

    if anchor_path and os.path.isfile(anchor_path):
        with open(anchor_path, "rb") as f:
            anchor_b64 = base64.b64encode(f.read()).decode()
    else:
        anchor_b64 = None

    if use_local:
        # ---- minis-model-use 路线 ----
        content: list[dict] = [{"type": "text", "text": prompt}]
        if anchor_b64:
            content.insert(0, {"type": "image_url",
                               "image_url": {"url": f"data:image/png;base64,{anchor_b64}"}})
        req = {
            "messages": [{"role": "user", "content": content}],
            "generation_config": {"size": size, "n": 1},
        }
        inp = os.path.join("/tmp", "baicat_gen_req.json")
        with open(inp, "w", encoding="utf-8") as f:
            json.dump(req, f, ensure_ascii=False)
        out_png = os.path.join("/tmp", "baicat_gen_out.png")
        if os.path.exists(out_png):
            os.remove(out_png)
        proc = subprocess.run(
            ["minis-model-use", "run", "--model", "gpt-image-2",
             "--endpoint", "images-gen", "--input", inp, "--output", out_png],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"minis-model-use 失败: {proc.stderr.strip()[:500]}")
        with open(out_png, "rb") as f:
            return f.read()

    # ---- IMAGE_API_URL 直调路线 ----
    body: dict = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "size": size,
        "quality": "high",
        "n": 1,
    }
    if anchor_b64:
        body["image"] = f"data:image/png;base64,{anchor_b64}"

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


def compose_multipanel(
    units: list[bytes],
    slots: list[dict],
    canvas_w: int = 1024,
    canvas_h: int = 1536,
    separator: tuple[int, int, int] = (217, 217, 217),
) -> bytes:
    """把 N 个分镜单元(字节)按布局模板拼成一张整页多格图。

    slot: {"x","y","w","h","rot"} —— (x,y) 目标左上角, w/h 目标尺寸, rot 微旋转角度。
    旋转后露白用 canvas 底纸色填充，并放大覆盖以防边角露出底纸。
    保留分镜单元顶部的留白区不被裁掉（加字用）。
    返回 JPEG 字节；内部异常时抛 raise，调用方可据此切换备用模板。
    """
    from PIL import Image
    if len(units) != len(slots):
        raise ValueError(f"分镜单元数 {len(units)} 与布局槽位数 {len(slots)} 不一致")

    # canvas 底纸色：取第一个单元顶部留白的平均色，尽量贴近原纸
    base_color = (244, 239, 230)
    try:
        probe = Image.open(BytesIO(units[0])).convert("RGB")
        w0, h0 = probe.size
        top_region = probe.crop((0, 0, min(w0, 200), min(h0, 60))).resize((1, 1))
        base_color = top_region.getpixel((0, 0))
    except Exception:
        pass

    canvas = Image.new("RGB", (canvas_w, canvas_h), base_color)

    # 按阅读顺序（slots 顺序即阅读顺序）依次贴入；z序=数组顺序，后者覆盖前者(允许重叠)
    for unit_bytes, slot in zip(units, slots):
        if slot is None:
            raise ValueError("布局中存在 None 槽位")
        img = Image.open(BytesIO(unit_bytes)).convert("RGB")
        sw, sh = img.size

        tx, ty, tw, th = (int(slot["x"]), int(slot["y"]),
                          int(slot["w"]), int(slot["h"]))
        rot = float(slot.get("rot", 0) or 0)

        # 1) 覆盖裁切到目标比例（居中，保留顶部留白优先：从顶部起算）
        body_aspect = tw / th if th else 1
        src_body_h = sh
        # 目标区域需要 src 比例匹配；以"宽度为准"覆盖，同时尽量保留顶部
        scale = max(tw / sw, th / sh)
        cw = max(int(tw / scale), 1)
        ch = max(int(th / scale), 1)
        # 裁剪：若原位图高宽比比目标"窄"(需要纵向较宽)，居中竖裁但顶部偏移=0 保顶部留白
        crop_x = max((sw - cw) // 2, 0)
        crop_y = 0  # 从顶部开始，保留留白
        if ch > sh:
            ch = sh
        crop = img.crop((crop_x, crop_y, crop_x + cw, crop_y + ch))

        # 2) 缩放并旋转（旋转用底色填充 + 放大覆盖，避免露白）
        tile = crop.resize((tw, th), Image.LANCZOS)
        if abs(rot) > 0.05:
            tile = tile.rotate(rot, resample=Image.BICUBIC,
                               expand=True, fillcolor=base_color)

        # 中心对齐到目标区域
        px = tx + (tw - tile.size[0]) // 2
        py = ty + (th - tile.size[1]) // 2
        canvas.paste(tile, (px, py))

    # 极淡浅灰分隔线：在相邻大小槽间隙处不强求（随旋转），整页画纸感即可。
    # 这里不强制加网格线，保持"有设计感"而非卡片感。如需分隔线由模板控制。
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
    ap.add_argument("--multipanel", action="store_true",
        help="整页多格模式（仅 colored-pencil）：默认自由艺术版，把 3-5 格/页拼进一张 1024x1536 "
             "整页（非等分节奏+微旋转）；多次调试失败自动降级规整节奏版。"
             "也可在 story JSON 里用 \"multipanel\": true 或 \"multipanel_style\": \"free|regular\" 开启。",
    )
    ap.add_argument("--mp-style", choices=["free", "regular"], default=None,
        help="整页多格排布风格：free=自由艺术版(默认) regular=规整节奏版")
    ap.add_argument("--page-native", action="store_true",
        help="整页原生生图（复制 craft-skills page-native 思路）：让 GPT 一次画出一整页多格漫画，"
             "而非逐格生成+拼接。story JSON 可用 \"page_native\": true 开启（须配合 multipanel）。")
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
    global _USE_MINI_MODEL
    # 生图路线：优先 IMAGE_API_URL 直调；未设置则回退 minis-model-use（GPT Image 2）。
    _USE_MINI_MODEL = False
    if not api_url:
        # minis-model-use 是 iSH 环境可用的生图代理
        import shutil as _sh
        if _sh.which("minis-model-use"):
            print("[生图] IMAGE_API_URL 未设置，改用 minis-model-use (GPT Image 2)")
            _USE_MINI_MODEL = True
            api_url = ""   # generate_panel 里据此走 minis 路线
        else:
            print("ERROR: 未找到 minis-model-use，且 IMAGE_API_URL 未设置", file=sys.stderr)
            return 1
    if not api_key and not _USE_MINI_MODEL:
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

    # ---- 整页多格模式判定 ----
    # 仅 colored-pencil；需要显式开启（CLI --multipanel 或 story JSON "multipanel": true）。
    # 总格数 ≥5 才启用；否则回退逐格单图。每页装 3-5 格，封面(首格)单独出单图。
    multipanel = (args.multipanel or bool(story.get("multipanel", False))) and style == "colored-pencil"
    if multipanel:
        multipanel = len(panels) >= 5
        if len(panels) < 5:
            print("⚠️  multipanel 已开启但总格数<5，回退为逐格单图。")
    mp_style = args.mp_style or story.get("multipanel_style", "free")
    if mp_style not in ("free", "regular"):
        mp_style = "free"
    # 整页原生生图：让 GPT 一次画整页多格（不逐格拼接）。仅 multipanel 且显式开启。
    page_native = bool(story.get("page_native", False)) or args.page_native
    if page_native and not multipanel:
        page_native = False
    # multipanel_cover: 默认 true（首格单独出封面单图）；false 则全部格进整页，不留独立封面。
    mp_cover = bool(story.get("multipanel_cover", True))
    print(f"Multipanel(整页多格): {'ON' if multipanel else 'OFF'}"
          + (f"  风格={mp_style}" if multipanel else ""))
    print()

    # 生成清单
    jobs = []
    if multipanel:
        if mp_cover:
            jobs.append({"type": "cover", "idx": 0, "panel": panels[0]})
            rest = list(range(1, len(panels)))
        else:
            rest = list(range(0, len(panels)))
        # 剩余格按每页 3-5 切分
        pages = _split_pages(len(rest))
        cursor = 0
        for page_idx, page_size in enumerate(pages):
            idxs = rest[cursor:cursor + page_size]
            cursor += page_size
            jobs.append({"type": "page", "page": page_idx + 1,
                         "idxs": idxs,
                         "panels": [panels[i] for i in idxs],
                         "style": mp_style,
                         "native": page_native})
    elif split2:
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
        # 两风格生图均不画字：doodle 与 colored-pencil 配方都不含【文字】占位符，
        # text 仅用于情绪推断与旁白规划。此处保留"配方含【文字】才填充"逻辑，便于未来配方扩展。
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
        elif job["type"] == "page":
            # 整页多格：page_native=让 GPT 一次画整页；否则生成本页分镜单元再拼成整页
            page_no = job["page"]
            idxs = job["idxs"]
            panels_of_page = job["panels"]
            n = len(idxs)
            page_out = os.path.join(args.output_dir, f"story_page_{page_no}.jpeg")
            if os.path.exists(page_out) and os.path.getsize(page_out) > 10000:
                print(f"[page {page_no}]: already composed, using existing")
                composed_paths.append(page_out)
                print(f"  ✅ {page_out}")
                sys.stdout.flush()
                continue

            # ---- 整页原生生图（page_native）----
            if job.get("native"):
                try:
                    page_tpl = extract_template("colored-pencil-page")
                except ValueError as e:
                    print(f"  ❌ [page {page_no}] 取整页配方失败: {e}", file=sys.stderr)
                    sys.stdout.flush()
                    continue
                # 构造整页布局描述：主锚点格 + 其余格，按阅读顺序
                layout_note = (
                    "A larger anchor panel at the top (the strongest/most emotional beat), "
                    "then the remaining panels below in reading order, sizes varying for rhythm. "
                    "Panels reading order top to bottom:"
                )
                layout_texts = []
                for k, p in zip(idxs, panels_of_page):
                    layout_texts.append(f"Panel {k+1}: {p.get('scene','')}")
                page_layout = layout_note + "\n" + "\n".join(layout_texts)
                page_fill = {"主体": page_layout, **var_values}
                try:
                    page_prompt = render(page_tpl, page_fill)
                except ValueError as e:
                    print(f"  ❌ [page {page_no}] 整页配方渲染失败: {e}", file=sys.stderr)
                    sys.stdout.flush()
                    continue
                print(f"[page {page_no}]: 整页原生生成 {n}格 (1024x1536)...")
                sys.stdout.flush()
                t0 = time.time()
                try:
                    img_bytes = generate_panel("", page_prompt, api_url, api_key,
                                               None, size="1024x1536")
                    with open(page_out, "wb") as f:
                        f.write(img_bytes)
                    composed_paths.append(page_out)
                    print(f"  ✅ {page_out} ({len(img_bytes)//1024}KB, 整页原生 {n}格, {time.time()-t0:.1f}s)")
                except Exception as e:
                    print(f"  ❌ [page {page_no}] 整页原生失败: {e}")
                sys.stdout.flush()
                continue

            # 生成每个分镜单元（方形，保像素）
            unit_paths = []
            for k, p in zip(idxs, panels_of_page):
                unit_job = {"idx": k, "panel": p, "unit_size": "square"}
                up = _generate_unit(unit_job, f"page{page_no} unit {k+1}")
                if not up:
                    print(f"⚠️  [page {page_no}] 分镜 {k+1} 生成失败，跳过整页")
                    break
                unit_paths.append(up)
            if len(unit_paths) != n:
                sys.stdout.flush()
                continue

            units_bytes = []
            ok_all = True
            for up in unit_paths:
                try:
                    with open(up, "rb") as f:
                        units_bytes.append(f.read())
                except Exception as e:
                    print(f"  ❌ [page {page_no}] 读取分镜单元失败: {e}")
                    ok_all = False
                    break
            if not ok_all:
                sys.stdout.flush()
                continue

            # 布局：先尝试 free，失败降级 regular（稳定可复现）
            if get_templates is None:
                print(f"  ❌ [page {page_no}] multipanel_layouts 未导入，无法拼图")
                sys.stdout.flush()
                continue
            attempt_styles = ["regular"] if job.get("style") == "regular" else ["free", "regular"]
            merged = None
            used_style = None
            for st in attempt_styles:
                tmpls = get_templates(n, st)
                if not tmpls:
                    continue
                for tmpl in tmpls:
                    try:
                        merged = compose_multipanel(units_bytes, tmpl)
                        used_style = st
                        break
                    except Exception as e:
                        print(f"  ⚠️  [page {page_no}] 布局({st})尝试失败: {e}")
                        merged = None
                if merged is not None:
                    break
            if merged is None:
                print(f"  ❌ [page {page_no}] 所有布局尝试均失败，跳过整页")
                sys.stdout.flush()
                continue
            with open(page_out, "wb") as f:
                f.write(merged)
            composed_paths.append(page_out)
            print(f"  ✅ {page_out} ({len(merged)//1024}KB, 整页{used_style}拼接完成, {n}格)")
        sys.stdout.flush()

    print("\nDone! All panels saved to:", args.output_dir)
    if composed_paths:
        print("组合图：")
        for p in composed_paths:
            print(f"  - {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
