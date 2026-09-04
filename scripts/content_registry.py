#!/usr/bin/env python3
"""content_registry.py — baicat V3 账号内容数据库（纯规则，不打分）

三个职责：
  1. register  登记一篇已发布作品
  2. check     新故事进候选池前：fingerprint 查重 + 30篇限额检查
  3. stats     输出近 N 篇组合统计（数据反哺原料）

设计原则：AI 不给自己打分。这里只有机械判定——
  fingerprint 完全相同 → BLOCK（换皮故事，禁止制作）
  ≥6/8 维相同          → WARN 要求改造
  限额超限             → LIMIT 强制提醒换维度
其余一律 PASS。真正的"好坏"交给发布数据。

用法:
  # 初始化数据库（首次）
  python3 content_registry.py --registry data/content_registry.json init

  # 检查新故事（--file 传 8 维 JSON，或逐个 --kv 传）
  python3 content_registry.py --registry data/content_registry.json check --file new_story_dims.json
  python3 content_registry.py --registry data/content_registry.json check \
      --relationship 父女 --theme 失去 --conflict 误会 --hook-type 异常事件 \
      --ending-type 余震定格 --emotion 遗憾 --setting 家庭 --object 早餐

  # 登记已发布作品（完整记录 JSON）
  python3 content_registry.py --registry data/content_registry.json register --file work.json

  # 近 N 篇组合统计
  python3 content_registry.py --registry data/content_registry.json stats --last 20

check 退出码：0 = 可进候选池（可能有 LIMIT 提醒）；1 = BLOCK（禁止制作）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

FINGERPRINT_KEYS = [
    "relationship", "theme", "conflict", "hook_type",
    "ending_type", "emotion", "setting", "object",
]
KEY_ALIASES = {  # 允许中文/连字符别名 → 标准键
    "relationship": ["relationship", "人物关系", "关系"],
    "theme": ["theme", "主题"],
    "conflict": ["conflict", "冲突", "冲突类型"],
    "hook_type": ["hook_type", "hook-type", "hooktype", "钩子", "钩子类型"],
    "ending_type": ["ending_type", "ending-type", "endingtype", "结局", "结局类型"],
    "emotion": ["emotion", "情绪", "主情绪"],
    "setting": ["setting", "场景"],
    "object": ["object", "道具", "核心道具"],
}

DEFAULT_LIMITS = {
    "relationship_consecutive": 2,                      # 同一关系 连续≤2
    "hook_consecutive": 2,                              # 同一钩子类型 连续≤2
    "theme_window": {"window": 10, "max": 2},           # 同一主题 10篇内≤2
    "ending_window": {"window": 5, "max": 1},           # 同一结局 5篇内≤1
    "object_window": {"window": 10, "max": 2},          # 同一道具 10篇内≤2
    "setting_window": {"window": 5, "max": 2},          # 同一场景 5篇内≤2
}


def load_registry(path: str) -> dict:
    if not os.path.isfile(path):
        print(f"ERROR: registry 不存在: {path}（先跑 init）", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("works", [])
    data.setdefault("limits", dict(DEFAULT_LIMITS))
    return data


def save_registry(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def norm_dims(raw: dict) -> dict:
    """把输入 dict 归一化成 8 个标准键；缺键报错。"""
    dims = {}
    for std_key, aliases in KEY_ALIASES.items():
        got = None
        for a in aliases:
            if raw.get(a) not in (None, ""):
                got = str(raw[a]).strip()
                break
        if got is None:
            raise ValueError(f"缺少维度: {std_key}（可用写法: {'/'.join(aliases)}）")
        dims[std_key] = got
    unknown = [k for k in raw if k not in [a for al in KEY_ALIASES.values() for a in al]]
    if unknown:
        print(f"[提示] 忽略未识别字段: {', '.join(sorted(unknown))}", file=sys.stderr)
    return dims


def fingerprint_str(dims: dict) -> str:
    return "-".join(dims[k] for k in FINGERPRINT_KEYS)


def check_fingerprint(dims: dict, works: list) -> tuple[list[str], list[str]]:
    """返回 (blocks, warns)。BLOCK=禁止制作；WARN=要求改造（不拦截脚本，流程里必须处理）。"""
    blocks: list[str] = []
    warns: list[str] = []
    for w in works:
        wd = {k: str(w.get(k, "")) for k in FINGERPRINT_KEYS}
        if wd == dims:
            blocks.append(
                f"❌ BLOCK: 与 {w.get('id','?')}《{w.get('title','?')}》fingerprint 完全相同"
                f"（{fingerprint_str(dims)}）→ 换皮故事，禁止制作"
            )
            return blocks, warns
    for w in works:
        wd = {k: str(w.get(k, "")) for k in FINGERPRINT_KEYS}
        same = [k for k in FINGERPRINT_KEYS if wd[k] == dims[k]]
        if len(same) >= 6:
            diff = [k for k in FINGERPRINT_KEYS if wd[k] != dims[k]]
            warns.append(
                f"⚠️ WARN: 与 {w.get('id','?')}《{w.get('title','?')}》有 {len(same)}/8 维相同"
                f"（相同: {'/'.join(same)}；不同: {'/'.join(diff)}）→ 至少改造 2 个维度再进候选池"
            )
    return blocks, warns


def check_limits(dims: dict, works: list, limits: dict) -> list[str]:
    """返回 LIMIT 行（提醒，不禁止）。works 按登记时间升序。"""
    out = []

    def recent(n: int) -> list[dict]:
        return works[-n:] if n > 0 else []

    # 连续型：relationship / hook_type
    for key, lim_name in (("relationship", "relationship_consecutive"),
                          ("hook_type", "hook_consecutive")):
        cap = int(limits.get(lim_name, 2))
        run = 0
        for w in reversed(works):
            if str(w.get(key, "")) == dims[key]:
                run += 1
            else:
                break
        if run >= cap:
            out.append(
                f"⚠️ LIMIT: {lim_name} 触顶 —— {key}={dims[key]} 最近已连续 {run} 篇"
                f"（上限 {cap}），强制提醒：换一个维度"
            )
        elif run == cap - 1:
            out.append(
                f"ℹ️ NOTE: {key}={dims[key]} 最近已连续 {run} 篇，再用本次将触顶（之后必须换）"
            )

    # 窗口型：theme / ending / object / setting
    for key, lim_name in (("theme", "theme_window"), ("ending_type", "ending_window"),
                          ("object", "object_window"), ("setting", "setting_window")):
        cfg = limits.get(lim_name, {})
        window, cap = int(cfg.get("window", 10)), int(cfg.get("max", 2))
        cnt = sum(1 for w in recent(window) if str(w.get(key, "")) == dims[key])
        if cnt >= cap:
            out.append(
                f"⚠️ LIMIT: {lim_name} 超限 —— {key}={dims[key]} 近 {window} 篇已出现 {cnt} 次"
                f"（上限 {cap}），强制提醒：换一个维度"
            )
        elif cnt > 0 and cnt == cap - 1:
            out.append(
                f"ℹ️ NOTE: {key}={dims[key]} 近 {window} 篇已出现 {cnt} 次，本次为最后一次额度"
            )
    return out


def cmd_init(args) -> int:
    if os.path.isfile(args.registry):
        print(f"registry 已存在: {args.registry}（不覆盖）")
        return 0
    save_registry(args.registry, {"_note": "baicat V3 账号内容数据库", "works": [],
                                  "limits": dict(DEFAULT_LIMITS)})
    print(f"✅ 已初始化: {args.registry}")
    return 0


def cmd_check(args) -> int:
    reg = load_registry(args.registry)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = {k: v for k, v in {
            "relationship": args.relationship, "theme": args.theme,
            "conflict": args.conflict, "hook_type": args.hook_type,
            "ending_type": args.ending_type, "emotion": args.emotion,
            "setting": args.setting, "object": args.object,
        }.items() if v}
    try:
        dims = norm_dims(raw)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    window = args.last if args.last and args.last > 0 else 30
    works = reg["works"][-window:]
    print(f"── baicat V3 选题检查（对比最近 {len(works)} 篇）──")
    print(f"[指纹] {fingerprint_str(dims)}")

    blocks, warns = check_fingerprint(dims, works)
    limits = check_limits(dims, works, reg.get("limits", DEFAULT_LIMITS))
    hard = [l for l in warns + limits if l.startswith("⚠️")]
    for line in warns + blocks + limits:
        print(line)
    if not blocks:
        print("✅ PASS: 可进候选池" + ("（⚠️ 提醒必须处理后再制作）" if hard else ""))
        return 0
    return 1


def cmd_register(args) -> int:
    reg = load_registry(args.registry)
    with open(args.file, encoding="utf-8") as f:
        work = json.load(f)
    missing = [k for k in FINGERPRINT_KEYS if work.get(k) in (None, "")]
    if missing:
        print(f"ERROR: 登记记录缺少维度字段: {', '.join(missing)}", file=sys.stderr)
        return 1
    work.setdefault("id", time.strftime("%Y%m%d") + "_%03d" % (len(reg["works"]) % 1000 + 1))
    work.setdefault("published_at", time.strftime("%Y-%m-%d"))
    reg["works"].append(work)
    save_registry(args.registry, reg)
    print(f"✅ 已登记 {work['id']}《{work.get('title','?')}》  当前共 {len(reg['works'])} 篇")
    return 0


def cmd_stats(args) -> int:
    reg = load_registry(args.registry)
    works = reg["works"][-args.last:] if args.last > 0 else reg["works"]
    if not works:
        print("（数据库为空，还没有登记作品）")
        return 0
    print(f"── 近 {len(works)} 篇组合统计 ──")
    for k in FINGERPRINT_KEYS:
        cnt: dict[str, int] = {}
        for w in works:
            v = str(w.get(k, ""))
            cnt[v] = cnt.get(v, 0) + 1
        top = sorted(cnt.items(), key=lambda x: -x[1])
        summary = " / ".join(f"{v}×{c}" for v, c in top[:4])
        print(f"  {k:<14}: {summary}")
    if args.with_metrics:
        print("\n── 已回填数据的作品（按完播率降序）──")
        rows = [w for w in works if w.get("completion") is not None]
        rows.sort(key=lambda w: -float(w.get("completion", 0)))
        for w in rows:
            print(f"  {w.get('id')}《{w.get('title','?')}》 完播 {w.get('completion')} "
                  f"评论 {w.get('comments', '?')} fingerprint={fingerprint_str({k: w.get(k, '') for k in FINGERPRINT_KEYS})}")
        if not rows:
            print("  （还没有回填发布数据的作品；发布后把划走率/完播率/评论数补进登记记录）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="baicat V3 账号内容数据库（fingerprint/限额/统计）")
    ap.add_argument("--registry", default=None, help="registry JSON 路径（默认 skill data/ 下）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    p_check = sub.add_parser("check")
    p_check.add_argument("--file", help="8 维 JSON 文件（支持中文/英文键名）")
    for std_key, aliases in KEY_ALIASES.items():
        flags = ["--" + a.replace("_", "-") for a in aliases]
        p_check.add_argument(*flags, dest=std_key, default=None)
    p_check.add_argument("--last", type=int, default=30, help="对比最近 N 篇（默认30）")
    p_check.set_defaults(func=cmd_check)
    p_reg = sub.add_parser("register")
    p_reg.add_argument("--file", required=True, help="完整作品记录 JSON（含 8 维字段）")
    p_reg.set_defaults(func=cmd_register)
    p_stats = sub.add_parser("stats")
    p_stats.add_argument("--last", type=int, default=20)
    p_stats.add_argument("--with-metrics", action="store_true", help="附带已回填数据的排序表")
    p_stats.set_defaults(func=cmd_stats)
    # 防呆：--registry 放在子命令之后也能识别（存到 registry_sub）
    for p in (p_check, p_reg, p_stats, sub.choices["init"]):
        p.add_argument("--registry", dest="registry_sub", default=None, help=argparse.SUPPRESS)

    args = ap.parse_args()
    sub_registry = getattr(args, "registry_sub", None)
    if sub_registry:
        args.registry = sub_registry
    if not args.registry:
        args.registry = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     "data", "content_registry.json")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
