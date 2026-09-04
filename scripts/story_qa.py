#!/usr/bin/env python3
"""story_qa.py — baicat V3 发布前 QA 检查单执行器

分工：AI 负责"逐项回答 pass/fail + 证据"，本脚本负责"对答案 + 汇总"。
只认 pass/fail，不打分、不评级——fail 项汇总成必改清单，改完复检。

四层 QA 清单（内置，--template 导出空白模板给 AI 填）：
  STORY QA    故事逻辑八项
  CONTENT QA  内容结构六项
  IMAGE QA    图像质量九项
  DEDUPE QA   去重六项

用法:
  # 1. 导出空白模板（AI 填写）
  python3 story_qa.py --template > qa_result.json

  # 2. AI 填完后汇总
  python3 story_qa.py --input qa_result.json

退出码：0 = 全部 PASS；1 = 存在 FAIL（输出必改清单）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time

QA_CHECKLIST = {
    "STORY_QA": [
        ("motivation", "人物动机成立"),
        ("timeline", "时间线成立"),
        ("space", "空间成立（人物位置/出入）"),
        ("info_source", "信息来源成立（谁在场谁知道）"),
        ("prop_flow", "道具流转成立（钱/物从哪来到哪去）"),
        ("twist_evidence", "反转/关键转折有证据支撑"),
        ("ending_causal", "结局有因果，不靠留白遮漏洞"),
        ("no_dumbing", "没有强行降智推进"),
    ],
    "CONTENT_QA": [
        ("first_panel_anomaly", "首图有异常/悬念"),
        ("curiosity_gap", "好奇缺口成立（提问→证据→解释节奏完整）"),
        ("first3_no_dead", "前3格无废镜头（异常→预期→阻力）"),
        ("midline_progress", "中段持续推进（每1-2格有新信息/阻力/选择/证据/人物/代价）"),
        ("last_panel_landing", "最后一格有落点"),
        ("comment_trigger", "评论区有讨论点"),
    ],
    "IMAGE_QA": [
        ("character_consistent", "人物外貌一致（跨格同脸）"),
        ("clothing_consistent", "服装一致"),
        ("prop_consistent", "关键道具外观一致"),
        ("scene_continuous", "场景连续（同场景不跳空间）"),
        ("composition_ok", "构图完整（主体不越界不被裁）"),
        ("no_hand_issue", "无明显手部/肢体问题"),
        ("no_stray_text", "无奇怪文字/乱码/水印"),
        ("blank_band_ok", "留白足够（顶部留白区干净可用）"),
        ("subject_clear", "画面主体明确不拥挤"),
    ],
    "DEDUPE_QA": [
        ("title_unique", "与最近30篇标题不重复"),
        ("structure_unique", "故事结构不过度重复"),
        ("theme_unique", "主题不过度重复"),
        ("ending_unique", "结局不过度重复"),
        ("hook_not_streak", "Hook 类型不连续重复"),
        ("visual_unique", "视觉元素（人物/场景/道具）不过度重复"),
    ],
}


def template() -> str:
    lines = {
        "story_json": "path/to/story.json",
        "output_dir": "path/to/output",
        "checked_at": "",
        "qa": {},
    }
    for layer, items in QA_CHECKLIST.items():
        lines["qa"][layer] = [
            {"item": item, "pass": None, "evidence": ""}
            for _, item in items
        ]
    return json.dumps(lines, ensure_ascii=False, indent=2)


def validate(data: dict) -> list[str]:
    errors = []
    qa = data.get("qa", {})
    for layer, items in QA_CHECKLIST.items():
        rows = qa.get(layer)
        if rows is None:
            errors.append(f"缺少 QA 层: {layer}")
            continue
        if len(rows) != len(items):
            errors.append(f"{layer}: 项目数 {len(rows)} ≠ 清单 {len(items)}（用 --template 重新生成）")
        for i, row in enumerate(rows):
            if row.get("pass") not in (True, False):
                std = items[i][1] if i < len(items) else f"第{i+1}项"
                errors.append(f"{layer}[{i+1}]「{row.get('item', std)}」未回答 pass=true/false")
    unknown = [k for k in qa if k not in QA_CHECKLIST]
    if unknown:
        errors.append(f"未知的 QA 层: {', '.join(unknown)}")
    return errors


def report(data: dict) -> int:
    qa = data.get("qa", {})
    fails, notes = [], []
    for layer, items in QA_CHECKLIST.items():
        std_map = {item: key for key, item in items}
        for row in qa.get(layer, []):
            item_name = row.get("item", "")
            key = std_map.get(item_name, item_name)
            if row.get("pass") is False:
                fails.append((layer, item_name, row.get("evidence", "") or "（未给证据）"))
            elif row.get("pass") is True and row.get("evidence"):
                notes.append((layer, item_name, row["evidence"]))
    print("━━━━━━━━━━━━━━")
    print("BAICAT V3 FINAL QA")
    print("━━━━━━━━━━━━━━")
    story = data.get("story_json", "?")
    print(f"故事: {story}")
    print(f"检查时间: {data.get('checked_at') or time.strftime('%Y-%m-%d %H:%M:%S')}")
    for layer in QA_CHECKLIST:
        rows = qa.get(layer, [])
        passed = sum(1 for r in rows if r.get("pass") is True)
        print(f"{layer:<12}: {passed}/{len(rows)} pass")
    if fails:
        print(f"\n❌ FAIL —— 必改 {len(fails)} 项：")
        for i, (layer, item, ev) in enumerate(fails, 1):
            print(f"  {i}. [{layer}] {item}")
            print(f"     证据: {ev}")
        print("\n改完后重新跑本脚本复检。")
        return 1
    if notes:
        print("\n📝 证据记录：")
        for layer, item, ev in notes:
            print(f"  [{layer}] {item} ← {ev}")
    print("\n✅ PASS —— 全部通过，可进入发布环节。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="baicat V3 发布前 QA 检查单执行器")
    ap.add_argument("--template", action="store_true", help="输出空白 QA 模板 JSON")
    ap.add_argument("--input", help="已填写的 QA 结果 JSON")
    args = ap.parse_args()

    if args.template:
        print(template())
        return 0
    if not args.input:
        ap.error("需要 --template 或 --input 之一")
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    errors = validate(data)
    if errors:
        print("❌ QA 结果不完整/不合法：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return report(data)


if __name__ == "__main__":
    raise SystemExit(main())
