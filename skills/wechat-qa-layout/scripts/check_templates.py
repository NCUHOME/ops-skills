#!/usr/bin/env python3
"""检查模板库：文件齐全、信息完整、示例合规，生成结果与快照逐字节一致。

用法：
  python3 check_templates.py                  # 检查全部模板（提 PR 前必须全部通过）
  python3 check_templates.py --update 模板名   # 重新生成该模板的快照：新增模板，或确认要改它的样子时

快照 snapshot.html 是模板示例的粘贴版代码。改了 scripts/ 里的公共代码后，旧模板的快照一个字节都不能变；
变了就说明改动影响了已有模板：要么改回去，要么在 PR 里写明原因，经维护人同意后再 --update。
"""

import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

FILES = ["template.json", "example.md", "preview.png", "snapshot.html"]
KEYS = ["order", "name", "account", "description", "source", "rights", "colors", "limits"]


def check(tid, cfg, update):
    d, errs = build.TEMPLATES / tid, []
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", tid):
        errs.append("模板名只能用小写字母、数字和连字符（例如 ncuhome-blue）")
    errs += [f"缺少文件 {f}" for f in FILES if not (d / f).exists() and not (update and f == "snapshot.html")]
    errs += [f"template.json 缺少「{k}」" for k in KEYS if not cfg.get(k)]
    if isinstance(cfg.get("source"), dict) and not cfg["source"].get("title"):
        errs.append("template.json 的 source 要写参考推文标题（title）")
    if not (d / "example.md").exists():
        return errs
    r = build.render_article(d / "example.md", template=str(d))
    errs += [f"示例不合规：{w}" for w in r["lint"]]
    snap = d / "snapshot.html"
    if update:
        snap.write_text(r["code"] + "\n", encoding="utf-8")
        print(f"   已更新快照 {snap}")
    elif snap.exists():
        old = snap.read_text(encoding="utf-8")
        if old != r["code"] + "\n":
            new_lines, old_lines = (r["code"] + "\n").splitlines(), old.splitlines()
            n = next((i for i, (x, y) in enumerate(zip(new_lines, old_lines)) if x != y), min(len(new_lines), len(old_lines)))
            errs.append(f"生成结果和快照不一致（第 {n + 1} 行起）。改动影响了这个模板，见本脚本说明")
    return errs


def main():
    ap = argparse.ArgumentParser(description="检查模板库")
    ap.add_argument("--update", metavar="模板名", help="重新生成该模板的快照")
    args = ap.parse_args()
    templates = build.list_templates()
    if args.update and args.update not in [t for t, _ in templates]:
        build.fail(f"模板库里没有「{args.update}」")
    orders = [cfg.get("order") for _, cfg in templates]
    bad = 0
    for tid, cfg in templates:
        errs = check(tid, cfg, args.update == tid)
        if orders.count(cfg.get("order")) > 1:
            errs.append(f"编号 order={cfg.get('order')} 和别的模板重复")
        print(f"{'✗' if errs else '✓'} {cfg.get('order', '?')}. {tid}（{cfg.get('name', '')}）")
        for e in errs:
            print(f"   - {e}")
        bad += bool(errs)
    print(f"\n{len(templates)} 个模板，{'全部通过' if not bad else f'{bad} 个有问题'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
