#!/usr/bin/env python3
"""Deterministically letter baicat panels (single or split2) into the top blank band.

在 baicat 已生成的无字图上，用 PIL 把旁白文字当作精确几何绘制到每格/每分镜顶部留白区。
文字逐字对准 manifest，可复现、可审计；不依赖 AI 二次重绘。

设计参考 CheshireMew/... 的 compose_panels.py 确定性排字思路，但针对 baicat 简化：
  - 用亮度检测自适应定位每格的顶部留白带（无需手填坐标，与 baicat 现有管线无缝结合）
  - 纯 PIL、无 numpy，适配 iSH/Alpine
  - 逐字字形检查（缺字报错，不画豆腐块）
  - 文字宽度自适应缩字号；放不下报错让用户改词，不静默溢出

用法:
  python3 letter_baicat.py --manifest letter.json

manifest 结构:
{
  "font_file": "/usr/share/fonts/noto/NotoSansCJK-Bold.ttc",
  "font_index": 2,                 // Noto Sans CJK SC Bold（简体粗体）
  "font_color": [30,30,30],        // 可选，默认近黑板
  "image_root": ".",               // 可选，图片相对路径的基目录
  "out_suffix": "_lettered",       // 可选，默认 "_lettered"
  "images": [
    { "file": "story_split_2_3.jpeg", "layout": "split2",
      "texts": ["旁白二", "旁白三"] },        // split2: 上→下
    { "file": "story_p8.jpeg", "layout": "single",
      "texts": ["旁白八"] }
  ]
}

如不指定 font_file，自动在常见路径搜索 Noto CJK Bold。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# 整页多格拼图依赖（与 generate_story 共用 compose_multipanel / get_templates）
try:
    from generate_story import compose_multipanel
    from multipanel_layouts import get_templates
    _MP_AVAILABLE = True
except Exception:  # noqa: BLE001
    _MP_AVAILABLE = False

MIN_FONT_SIZE = 26          # 最小可接受字号（再小就报错让用户精简）
DEFAULT_FONT_SIZE = 46      # 初始口号
SAMPLE_STEP = 4             # 亮度采样步长（每 STEP 像素取一行检测）
BAND_MIN_HEIGHT = 20        # 留白带最小高度（低于可能不是留白）
MARGIN_X = 24               # 文字左右安全边距
MARGIN_TOP_BOTTOM = 12      # 文字与留白带上下的安全边距

NOTO_CJK_CANDIDATES = [
    "/usr/share/fonts/noto/NotoSansCJK-Bold.ttc",   # Linux/iSH
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/PingFang.ttc",           # macOS
]


class LetterError(ValueError):
    """确定性落字的可报告错误（缺字/放不下/无留白等），报告后由用户处理。"""


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_font_file(font_file: str | None, font_index: int) -> tuple[str, int]:
    """查找中文字体。若指定 font_file 直接用它；否则自动搜索候选。"""
    if font_file:
        if not os.path.isfile(font_file):
            raise LetterError(f"指定的字体文件不存在: {font_file}")
        return font_file, font_index
    for cand in NOTO_CJK_CANDIDATES:
        if os.path.isfile(cand):
            print(f"[字体] 使用 {cand} (index={font_index})")
            return cand, font_index
    raise LetterError(
        "未找到中文字体。请安装 font-noto-cjk (apk add font-noto-cjk) 或用 "
        "--manifest 的 font_file 指定字体路径。"
    )


def load_font(font_file: str, font_index: int, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(font_file, size, index=font_index)
    except Exception as e:  # noqa: BLE001
        raise LetterError(f"无法加载字体 {font_file} index={font_index}: {e}")


def missing_glyphs(font: ImageFont.FreeTypeFont, text: str) -> list[str]:
    """返回缺字字符列表（字体无法渲染的字形）。"""
    missing: list[str] = []
    for ch in text:
        if ch in (" ", "\n", "\r", "\t"):
            continue
        try:
            if font.getmask(ch).getbbox() is None:
                missing.append(ch)
        except Exception:  # noqa: BLE001
            missing.append(ch)
    return missing


def find_top_blank_band(img: Image.Image, y_start: int, y_end: int) -> tuple[int, int] | None:
    """在 [y_start, y_end) 内找顶部连续亮带（留白区）。

    返回 (top, bottom)，不含则 None。用亮度阈值：取全区最高亮度-10 作为"亮即留白"判据，
    从 y_start 起找第一个稳定亮带。
    """
    w, h = img.size
    gray = img.convert("L")
    pix = gray.load()

    def band_lum(y) -> float:
        s = 0
        for x in range(0, w, SAMPLE_STEP):
            s += pix[x, y]
        return s / max(1, w // SAMPLE_STEP)

    rows = [band_lum(y) for y in range(y_start, min(y_end, h))]
    if not rows:
        return None
    peak = max(rows)
    threshold = peak - 10

    # 从顶部找连续亮行组成带
    best: list[int] = []
    cur: list[int] = []
    for idx, val in enumerate(rows):
        y = y_start + idx
        if val > threshold:
            cur.append(y)
        else:
            if len(cur) >= BAND_MIN_HEIGHT and len(cur) > len(best):
                best = cur
            cur = []
    if len(cur) >= BAND_MIN_HEIGHT and len(cur) > len(best):
        best = cur

    if not best:
        return None
    return best[0], best[-1]


def fit_text_block(
    text: str,
    font_file: str,
    font_index: int,
    band: tuple[int, int],
    width: int,
    target_size: int = DEFAULT_FONT_SIZE,
) -> tuple[str, int, list[str], ImageFont.FreeTypeFont]:
    """把文字适配进留白带。返回 (有效文本, 字号, 行列表, 字体)。

    - 单行：文字水平居中、垂直居中于留白带。
    - 若文字是"单行超长"，尝试自动缩字号直到能放下；低于 MIN_FONT_SIZE 仍放不下则报错。
    - 支持多行：换行符 '\\n' 分隔的多行，行间 gap；总高超过留白带报错。
    """
    lines = text.split("\n")
    lines = [ln.strip() for ln in lines if ln.strip()]
    if not lines:
        raise LetterError("text 为空")

    # ---- 旁白排版规范（对齐 baicat 标准）----
    total_chars = sum(len(ln) for ln in lines)
    if len(lines) > 2:
        raise LetterError(
            f"旁白最多两行（当前 {len(lines)} 行），不允许通篇多行堆叠: {text!r}"
        )
    if len(lines) == 1 and total_chars > 20:
        raise LetterError(
            f"单行旁白最多 20 字（当前 {total_chars} 字）: {text!r}。请精简。"
        )
    if len(lines) == 2 and total_chars > 35:
        raise LetterError(
            f"两行旁白总字数最多 35 字（当前 {total_chars} 字）: {text!r}。请精简。"
        )

    band_top, band_bot = band
    avail_height = band_bot - band_top
    if avail_height < MIN_FONT_SIZE:
        raise LetterError(
            f"留白带高度 {avail_height}px 过小，无法放置文字。"
        )

    avail_w = width - 2 * MARGIN_X
    if avail_w < 10:
        raise LetterError("画布宽度过小")

    size = target_size
    while size >= MIN_FONT_SIZE:
        font = load_font(font_file, font_index, size)
        # 缺字检查
        for ln in lines:
            miss = missing_glyphs(font, ln)
            if miss:
                raise LetterError(
                    f"字体缺少字形: {''.join(miss)}（文本: {ln!r}）。"
                )
        # 行宽
        draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        metrics = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
        widths = [m[2] - m[0] for m in metrics]
        heights = [m[3] - m[1] for m in metrics]
        total_h = sum(heights) + int(size * 0.15) * (len(heights) - 1)
        fits_w = all(w <= avail_w for w in widths)
        fits_h = total_h <= avail_height - 2 * MARGIN_TOP_BOTTOM
        if fits_w and fits_h:
            return "\n".join(lines), size, lines, font
        size -= 4

    raise LetterError(
        f"文字放不进留白带(高{avail_height}px): {text!r}。"
        f"请精简为单行≤20字（或复杂节点两行≤35字），再重试。"
    )


def render_lines(
    img: Image.Image,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    band: tuple[int, int],
    color: tuple[int, int, int],
    target_size: int,
) -> list[dict[str, Any]]:
    """在留白带内水平居中、垂直居中绘制多行黑色粗体文字。返回每行渲染记录。"""
    draw = ImageDraw.Draw(img)
    mixs = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
    widths = [m[2] - m[0] for m in mixs]
    heights = [m[3] - m[1] for m in mixs]
    gap = int(target_size * 0.15)
    total_h = sum(heights) + gap * (len(heights) - 1)

    band_top, band_bot = band
    avail_h = band_bot - band_top
    cursor_y = band_top + (avail_h - total_h) // 2

    records: list[dict[str, Any]] = []
    w = img.size[0]
    for ln, mx, mh in zip(lines, mixs, heights):
        cw = mx[2] - mx[0]
        x = (w - cw) // 2 - mx[0]
        y = cursor_y - mx[1]
        draw.text((x, y), ln, font=font, fill=color)
        ink = draw.textbbox((x, y), ln, font=font)
        records.append({
            "text": ln,
            "ink_bbox": list(ink),
        })
        cursor_y += mh + gap
    return records


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Deterministically letter baicat panels (manifest 或 --auto 自动模式)"
    )
    ap.add_argument("--manifest", default=None, help="Path to lettering manifest JSON")
    ap.add_argument("--layout", choices=["single", "split2"], default=None,
                    help="Override layout for all images (optional)")
    ap.add_argument("--auto", action="store_true",
                    help="自动模式：从 story JSON + 产物目录自动找图并按序加字")
    ap.add_argument("--story-json", default=None, help="auto 模式：story JSON 路径")
    ap.add_argument("--output-dir", default=".", help="auto 模式：已生成产物目录")
    ap.add_argument("--image-root", default=None,
                    help="图片基目录（默认=manifest.image_root 或 auto 的 output-dir）")
    return ap


def letter_image(
    src: Path,
    layout: str,
    texts: list[str],
    font_file: str,
    font_index: int,
    color: tuple[int, int, int],
    out_suffix: str,
    mp_units: list[Path] | None = None,
) -> None:
    """对已生成的图确定性加字。layout: single|split2|multipanel。

    multipanel（整页多格）：不直接改整页图，而是对分镜单元逐个加字，再用
    compose_multipanel 按布局拼成带字整页。mp_units 为该页分镜单元路径列表。
    """
    if layout == "multipanel":
        if not _MP_AVAILABLE:
            raise LetterError("import generate_story/multipanel_layouts 失败，无法做整页多格加字")
        if not mp_units or len(mp_units) != len(texts):
            raise LetterError(
                f"multipanel 加字需要 mp_units(单元路径)与 texts 数量一致: 单元={len(mp_units or [])} 文字={len(texts)}"
            )
        # 对每个分镜单元单独加字到底部留白，再拼成带字整页
        lettered_units: list[bytes] = []
        for up, ttext in zip(mp_units, texts):
            if not up.is_file():
                raise LetterError(f"multipanel 分镜单元不存在: {up}")
            img = Image.open(up).convert("RGB")
            w, h = img.size
            band = find_top_blank_band(img, 0, int(h * 0.5))
            if band is None:
                raise LetterError(f"{up}: 未检测到顶部留白区，无法放置文字")
            valid, size, lines, font = fit_text_block(
                ttext, font_file, font_index, band, w, DEFAULT_FONT_SIZE
            )
            render_lines(img, lines, font, band, color, size)
            print(f"    {up.name}: {ttext!r} (字号{size}px)")
            buf = BytesIO()
            img.save(buf, format="PNG")
            lettered_units.append(buf.getvalue())

        # 布局：优先 free，失败降级 regular（与生成端一致）
        n = len(texts)
        merged = None
        used_style = None
        for st in (["regular"] if os.environ.get("MP_STYLE") == "regular" else ["free", "regular"]):
            for tmpl in get_templates(n, st):
                try:
                    merged = compose_multipanel(lettered_units, tmpl)
                    used_style = st
                    break
                except Exception:  # noqa: BLE001
                    merged = None
            if merged is not None:
                break
        if merged is None:
            raise LetterError(f"multipanel 所有布局尝试均失败（{n}格）")

        out_name = src.stem + out_suffix + ".jpeg"
        out_path = src.with_name(out_name)
        tmp = out_path.with_name(out_path.stem + ".tmp.png")
        with open(tmp, "wb") as f:
            f.write(merged)
        os.replace(tmp, out_path)

        ledger = {
            "source_page": str(src),
            "source_units": [str(u) for u in mp_units],
            "output": str(out_path),
            "font_file": font_file,
            "font_index": font_index,
            "font_color": list(color),
            "layout": "multipanel",
            "style": used_style,
            "images_texts": texts,
        }
        with open(out_path.with_suffix(".ledger.json"), "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {out_path} (整页多格 {n}格, {used_style})")
        return

    img = Image.open(src).convert("RGB")
    w, h = img.size
    print(f"[+字] {src}  {w}x{h}  layout={layout}")

    if layout == "split2":
        # 双分镜拼接图：上下两半（中间有 ~8px 淡灰细线）。分别对两半顶部做留白检测。
        upper_band = find_top_blank_band(img, 0, h // 2)
        lower_band = find_top_blank_band(img, (h // 2) + 8, h)
        bands = [upper_band, lower_band]
    else:
        bands = [find_top_blank_band(img, 0, int(h * 0.5))]

    if len(bands) != len(texts):
        raise LetterError(
            f"{src}: layout={layout} 检测到 {len(bands)} 个留白区，但给 {len(texts)} 段文字"
        )

    for idx_t, (band, ttext) in enumerate(zip(bands, texts)):
        if band is None:
            raise LetterError(f"{src}: 未检测到第 {idx_t+1} 个留白区，无法放置文字")
        target_size = DEFAULT_FONT_SIZE
        valid, size, lines, font = fit_text_block(
            ttext, font_file, font_index, band, w, target_size
        )
        render_lines(img, lines, font, band, color, size)
        label = f"  分镜{idx_t+1}  {ttext!r} (字号{size}px)"
        if len(lines) > 1:
            label += " [多行]"
        print(label)

    out_name = src.stem + out_suffix + src.suffix
    out_path = src.with_name(out_name)
    tmp = out_path.with_name(out_path.stem + ".tmp.png")
    img.save(tmp, "JPEG", quality=95)
    os.replace(tmp, out_path)

    # ledger
    ledger = {
        "source": str(src),
        "source_sha256": sha256_path(src),
        "output": str(out_path),
        "font_file": font_file,
        "font_index": font_index,
        "font_color": list(color),
        "layout": layout,
        "size": (w, h),
        "images_texts": texts,
    }
    ledger_name = out_path.with_suffix(".ledger.json")
    with open(ledger_name, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {out_path}")


def parse_font_color(raw: Any) -> tuple[int, int, int]:
    """解析颜色：支持 [r,g,b] 数组 或 "#rrggbb" 字符串。"""
    if isinstance(raw, list) and len(raw) == 3:
        return (int(raw[0]), int(raw[1]), int(raw[2]))
    if isinstance(raw, str):
        h = raw.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return (30, 30, 30)


def _split_pages_mp(n: int, min_p=3, max_p=5) -> list[int]:
    """把 n 个分镜切成若干页，每页 3-5 格，尽量贴近 4 格/页（与 generate_story 逻辑一致）。"""
    if n <= 0:
        return []
    if n <= max_p:
        return [n]
    # 目标每页 4 格
    pages_n = max(1, round(n / 4))
    base, rem = divmod(n, pages_n)
    sizes = [base + 1 if i < rem else base for i in range(pages_n)]
    # 校验：若出现 <min_p 或 >max_p 的页，兜底用贪婪切成 3-5 块
    if all(min_p <= s <= max_p for s in sizes) and sum(sizes) == n:
        return sizes
    rebuilt = []
    t = n
    while t > 0:
        take = min(max_p, t)
        if t - take == 1:  # 避免最后剩 1
            take -= 1
        if take < 1:
            take = 1
        rebuilt.append(take)
        t -= take
    return rebuilt


def build_auto_manifest(
    story_path: Path,
    output_dir: Path,
    image_root: Path,
) -> list[dict[str, Any]]:
    """从 story JSON + 产物目录自动构建 images 清单。

    映射依赖 generate_story.py 的产物命名：
      - 首格封面/单格:  story_<panel.id>.jpeg
      - 双分镜:          story_split_<idx+1>_<idx+2>.jpeg （数字为 1-based panels 顺序）
    对每个 panel，把其 text 填到对应产品文件的对应分镜。
    """
    story = load_json(story_path)
    panels = story.get("panels", [])
    if not panels:
        raise LetterError(f"story JSON 无 panels: {story_path}")

    split2 = bool(story.get("split2", False)) and len(panels) > 6
    multipanel = bool(story.get("multipanel", False)) and len(panels) >= 5

    images: list[dict[str, Any]] = []
    seen: dict[tuple, int] = {}  # (layout, file) -> 已分配的 texts 长度

    # 封面/首格
    cover_id = panels[0]["id"]
    cover_f = image_root / f"story_{cover_id}.jpeg"
    if cover_f.is_file():
        images.append({"file": f"story_{cover_id}.jpeg", "layout": "single",
                       "texts": [panels[0].get("text", "")]})
    else:
        print(f"⚠️  封面文件未找到，跳过: {cover_f}")

    if multipanel:
        # 整页多格：story_page_<n>.jpeg 每页装 3-5 格，按 _split_pages 映射。
        # 用分镜单元(方形)逐个加字再拼，比在整页图上定位留白更可靠。
        rest = list(range(1, len(panels)))
        pages = _split_pages_mp(len(rest))
        cursor = 0
        for page_no, page_size in enumerate(pages, 1):
            idxs = rest[cursor:cursor + page_size]
            cursor += page_size
            fname = f"story_page_{page_no}.jpeg"
            fpath = image_root / fname
            units = [str(image_root / f"story_{panels[i]['id']}.jpeg") for i in idxs]
            if fpath.is_file():
                texts = [panels[i].get("text", "") for i in idxs]
                images.append({"file": fname, "layout": "multipanel",
                               "texts": texts, "mp_units": units})
            else:
                # 整页文件可能是由单元拼出的；若不强制整页存在，直接按单元加字也可。
                if all(Path(u).is_file() for u in units):
                    images.append({"file": f"story_page_{page_no}.jpeg",
                                   "layout": "multipanel",
                                   "texts": texts, "mp_units": units})
                else:
                    print(f"⚠️  整页{page_no}的分镜单元不全，跳过: {units}")
    elif split2:
        # 双分镜：第2格起两两配对
        i = 1
        while i < len(panels):
            if i + 1 < len(panels):
                fname = f"story_split_{i+1}_{i+2}.jpeg"
                fpath = image_root / fname
                if fpath.is_file():
                    images.append({"file": fname, "layout": "split2",
                                   "texts": [panels[i].get("text", ""),
                                             panels[i + 1].get("text", "")]})
                else:
                    print(f"⚠️  双分镜文件未找到，跳过: {fpath}")
                i += 2
            else:
                # 末尾单格
                fname = f"story_{panels[i]['id']}.jpeg"
                fpath = image_root / fname
                if fpath.is_file():
                    images.append({"file": fname, "layout": "single",
                                   "texts": [panels[i].get("text", "")]})
                else:
                    print(f"⚠️  末尾单格文件未找到，跳过: {fpath}")
                i += 1
    else:
        # 逐格单图（≤6格或未开 split2）
        for p in panels:
            fname = f"story_{p['id']}.jpeg"
            fpath = image_root / fname
            if fpath.is_file():
                images.append({"file": fname, "layout": "single",
                               "texts": [p.get("text", "")]})
            else:
                print(f"⚠️  单格文件未找到，跳过: {fpath}")

    return images


def main() -> int:
    args = arg_parser().parse_args()

    # 支持两种入口：manifest 文件（含 "auto": true）或 纯命令行 --auto
    if args.manifest:
        manifest = load_json(Path(args.manifest))
    else:
        manifest = {}

    auto_mode = args.auto or manifest.get("auto", False)
    if auto_mode:
        story_path = Path(args.story_json or manifest.get("story_json", ""))
        if not story_path.is_file():
            print("❌ auto 模式需要 story JSON（--story-json 或 manifest.story_json）")
            return 1
        output_dir = Path(args.output_dir or manifest.get("output_dir", "."))
        image_root = Path(
            args.image_root or manifest.get("image_root", str(output_dir))
        )
        images = build_auto_manifest(story_path, output_dir, image_root)
        if not images:
            print("⚠️  未找到任何可加字的产物图，请检查 output_dir / image_root 路径。")
            return 1
    else:
        if not args.manifest:
            print("❌ 需要 --manifest 或 --auto。运行 --help 查看用法。")
            return 1
        image_root = Path(manifest.get("image_root", "."))
        images = manifest.get("images", [])

    font_file_raw = manifest.get("font_file")
    font_index = int(manifest.get("font_index", 2))
    color = parse_font_color(manifest.get("font_color", [30, 30, 30]))
    font_file, font_index = find_font_file(font_file_raw, font_index)
    out_suffix = manifest.get("out_suffix", "_lettered")

    for it in images:
        rel = it["file"]
        src = Path(image_root) / rel
        if not src.is_file():
            print(f"⚠️  跳过（不存在）: {rel}")
            continue
        layout = args.layout or it.get("layout", "single")
        texts = it.get("texts", [])
        mp_units = None
        if layout == "multipanel":
            mp_units = [Path(image_root) / str(u) for u in (it.get("mp_units") or [])]
        letter_image(src, layout, texts, font_file, font_index, color, out_suffix,
                     mp_units=mp_units)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
