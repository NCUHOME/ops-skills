#!/usr/bin/env python3
"""生成「模板一览」网页：每个模板一张卡片（编号、缩略图、名称、公众号、特点、来源），最后一张是「照一篇新推文做」。

用法：
  python3 gallery.py [-o 模板一览.html]      # 默认写到当前文件夹
  python3 gallery.py --list                  # 只在终端列出编号和名称

缩略图内嵌在网页里，生成的文件单独发给别人也能看。编号就是选择模板时用的编号。
"""

import argparse
import base64
import html
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>模板一览</title>
<style>
:root { --page: #edf1ed; --ink: #1f2a21; --muted: #667168; --line: #d5ddd5; --green: rgb(67, 156, 75); }
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 14px/1.6 -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; }
main { max-width: 1120px; margin: 0 auto; padding: 28px 16px 48px; }
h1 { margin: 0; font-size: 22px; }
.lead { margin: 4px 0 20px; color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 18px; }
.card { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 0 0 1px var(--line), 0 8px 24px rgba(31, 42, 33, .08);
  display: flex; flex-direction: column; }
.shot { aspect-ratio: 375 / 560; overflow: hidden; background: #f6f7f6; border-bottom: 1px solid var(--line); }
.shot img { width: 100%; display: block; }
.info { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 4px; }
.no { display: inline-block; min-width: 26px; padding: 0 8px; border-radius: 999px; background: var(--green); color: #fff;
  font-weight: 700; text-align: center; margin-right: 6px; }
.name { font-size: 16px; font-weight: 700; }
.meta { color: var(--muted); font-size: 13px; }
.src a { color: #576b95; }
.new .shot { display: grid; place-items: center; color: var(--green); font-size: 44px; font-weight: 300; background: #f3f8f3; }
</style>
</head>
<body>
<main>
<h1>模板一览</h1>
<p class="lead">回复编号选择模板；想照一篇新推文的样子做，选最后一项。</p>
<div class="grid">
__CARDS__
</div>
</main>
</body>
</html>
"""


def cards():
    out = []
    for i, (tid, cfg) in enumerate(build.list_templates(), 1):
        png = build.TEMPLATES / tid / "preview.png"
        thumb = (f'<img alt="{html.escape(cfg["name"])}" src="data:image/png;base64,'
                 f'{base64.b64encode(png.read_bytes()).decode()}">') if png.exists() else ""
        src = cfg.get("source") or {}
        title = html.escape(src.get("title", ""))
        link = f'<a href="{html.escape(src["url"])}">{title}</a>' if src.get("url") else title
        out.append(f'''<div class="card"><div class="shot">{thumb}</div><div class="info">
  <div><span class="no">{i}</span><span class="name">{html.escape(cfg["name"])}</span></div>
  <div class="meta">{html.escape(cfg.get("account", ""))} · 模板名 {tid}</div>
  <div>{html.escape(cfg.get("description", ""))}</div>
  <div class="meta src">参考：{link}</div></div></div>''')
    n = len(out) + 1
    out.append(f'''<div class="card new"><div class="shot">＋</div><div class="info">
  <div><span class="no">{n}</span><span class="name">照一篇新推文做</span></div>
  <div>给一篇已发布推文的链接，复刻它的版式排这次的文案；做完可以存进模板库。</div></div></div>''')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="生成模板一览网页")
    ap.add_argument("-o", "--out", type=Path, default=Path("模板一览.html"))
    ap.add_argument("--list", action="store_true", help="只在终端列出")
    args = ap.parse_args()
    if args.list:
        for i, (tid, cfg) in enumerate(build.list_templates(), 1):
            print(f"{i}. {cfg['name']}（{cfg.get('account', '')}，模板名 {tid}）：{cfg.get('description', '')}")
        print(f"{len(build.list_templates()) + 1}. 照一篇新推文做（导入新模板）")
        return
    args.out.write_text(PAGE.replace("__CARDS__", cards()), encoding="utf-8")
    print(f"写入 {args.out.resolve()}")


if __name__ == "__main__":
    main()
