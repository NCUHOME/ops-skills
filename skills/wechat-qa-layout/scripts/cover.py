#!/usr/bin/env python3
"""公众号封面：按模板 template.json 里的 cover 设置，给每篇文案画一张封面。

用法：
  python3 cover.py 文章.md [更多.md ...] [-o 输出目录] [--template 模板]

每篇输出两张：
  封面_<文件名>.png        2350×1000：上传公众号时，2.35:1 用整张，1:1 框住右边的正方形
  封面_<文件名>_1比1.png   1000×1000：右边那块正方形，单独预览或直接用

样式「清爽实景」（photo）：实拍照片在左，向右渐隐成浅色；右边的正方形里放 logo、「栏目｜期数」、
小字、大字和一行关键词。不用 emoji，也不用手绘图标。文字和底图取信息区（写法见 references/FORMAT.md）：
  封面        小字 / 大字（大字两边的括号会去掉）。不写就按同样规则拆「头图」：最后一行是大字，前面连起来是小字
  封面标签     一行关键词，用 / 或 、 隔开。不写就不显示
  封面图       换一张底图（相对本 .md 的路径）。不写就用模板自带的照片
  封面图位置    调整底图，例如「放大1.3 上移40% 左移10% 翻转」
需要 Chrome 或 Edge（无头模式截图）。字体优先用思源黑体（Noto Sans SC），找不到就用系统黑体。
"""

import argparse
import base64
import html
import mimetypes
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
from thumbnail import find_browser  # noqa: E402

W, H = 1175, 500          # CSS 像素，按 2 倍截图 → 2350×1000
SQ = W - H                # 右边正方形的左边界
TEXT_W = H - 86           # 文字区宽度：左边距 46，右边至少留 40
FONT = "explainer-kit/video/public/fonts/NotoSansSC-VF.woff2"  # 做视频 skill 装好的引擎里带着思源黑体


def data_uri(path):
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def find_font(cover, tpl_dir, base):
    """思源黑体文件：模板里指定的 → ~/explainer-kit → 文案所在文件夹往上找 explainer-kit。找不到返回 None。"""
    spots = [tpl_dir / cover["font"]] if cover.get("font") else []
    spots += [Path.home() / FONT] + [p / FONT for p in [base.resolve(), *base.resolve().parents]]
    return next((p for p in spots if p.is_file()), None)


def photo_setting(meta, cover, tpl_dir, base):
    """底图和摆放：(图片路径, 放大倍数, 上移, 左移, 翻转)。上移、左移按照片自身的高、宽算。"""
    p = cover["photo"]
    if meta.get("封面图"):
        path, zoom, up, left, flip = base / meta["封面图"], 1.0, None, 0.0, False
        if not path.is_file():
            build.fail(f"找不到封面图：{path}")
    else:
        path, zoom, up, left, flip = tpl_dir / p["file"], p.get("zoom", 1.0), p.get("up"), p.get("left", 0.0), p.get("flip", False)
    adj = meta.get("封面图位置", "")
    if m := re.search(r"放大\s*([\d.]+)", adj):
        zoom = float(m.group(1))
    if m := re.search(r"上移\s*([\d.]+)\s*%", adj):
        up = float(m.group(1)) / 100
    if m := re.search(r"左移\s*([\d.]+)\s*%", adj):
        left = float(m.group(1)) / 100
    if "翻转" in adj:
        flip = "不翻转" not in adj
    return path, zoom, up, left, flip


def fit(text, size, spacing=0):
    """字号：一行放进文字区，最大 size。"""
    em = build.width_em(text)
    return min(size, int((TEXT_W - spacing * len(text)) / em)) if em else size


def page(texts, photo, cover, logo, font, shift=0):
    """shift>0 时把画面左移、只露出右边的正方形（用来单独截 1:1）。"""
    head, small, big, tags = texts
    path, zoom, up, left, flip = photo
    c = cover["colors"]
    # 照片按宽度放大，至少铺满高度；不写「上移」就上下居中
    place = (f"top: 0; transform: translate({-left * 100:.2f}%, {-up * 100:.2f}%)" if up is not None
             else f"top: 50%; transform: translate({-left * 100:.2f}%, -50%)") + (" scaleX(-1)" if flip else "")
    face = (f'@font-face {{ font-family: "CoverSans"; src: url("{font.as_uri()}") format("woff2"); font-weight: 100 900; }}'
            if font else "")
    rows = [f'<div class="t1" style="font-size: {fit(head, 34, .5)}px">{html.escape(head)}</div>']
    if small:
        rows.append(f'<div class="t2" style="font-size: {fit(small, 19)}px">{html.escape(small)}</div>')
    rows += ['<div class="bar"></div>', f'<div class="big" style="font-size: {fit(big, 64, 3)}px">{html.escape(big)}</div>']
    if tags:
        rows.append(f'<div class="tags" style="font-size: {fit(tags, 16, 1)}px">{html.escape(tags)}</div>')
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
{face}
* {{ margin: 0; box-sizing: border-box; }}
html, body {{ width: {H if shift else W}px; height: {H}px; overflow: hidden; }}
.canvas {{ position: absolute; left: {-shift}px; top: 0; width: {W}px; height: {H}px; overflow: hidden;
  background: linear-gradient(90deg, {c["bg"][0]}, {c["bg"][1]});
  font-family: "CoverSans", "Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif; }}
.layer {{ position: absolute; inset: 0; }}
.fade {{ -webkit-mask-image: linear-gradient(90deg, #000 34%, rgba(0, 0, 0, .55) 48%, rgba(0, 0, 0, .12) 58%, transparent 64%); }}
.photo {{ position: absolute; left: 0; {place}; width: {zoom * W:.0f}px; min-height: {H}px; object-fit: cover;
  filter: saturate(1.08) contrast(1.03) brightness(1.03); }}
.glow {{ background: radial-gradient(ellipse 34% 62% at 80% 50%, rgba(255, 255, 255, .85), rgba(255, 255, 255, 0) 70%); }}
.text {{ position: absolute; left: {SQ + 46}px; top: 0; width: {TEXT_W}px; height: {H}px;
  display: flex; flex-direction: column; justify-content: center; }}
.logo {{ width: 190px; margin-bottom: 30px; }}
.t1 {{ font-weight: 900; color: {c["title"]}; letter-spacing: .5px; white-space: nowrap; line-height: 1.2; }}
.t2 {{ margin-top: 10px; font-weight: 700; color: {c["subtitle"]}; white-space: nowrap; }}
.bar {{ width: 40px; height: 4px; border-radius: 2px; background: {c["bar"]}; margin-top: 24px; }}
.big {{ align-self: flex-start; margin-top: 12px; font-weight: 900; letter-spacing: 3px; line-height: 1.1; white-space: nowrap;
  background: linear-gradient(90deg, {c["big"][0]}, {c["big"][1]}); -webkit-background-clip: text; color: transparent; }}
.tags {{ margin-top: 14px; font-weight: 600; color: {c["tags"]}; letter-spacing: 1px; white-space: nowrap; }}
</style></head><body><div class="canvas">
<div class="layer fade"><img class="photo" src="{data_uri(path)}" alt=""></div>
<div class="layer glow"></div>
<div class="text">
  {f'<img class="logo" src="{data_uri(logo)}" alt="logo">' if logo else ''}
  {"".join(rows)}
</div></div></body></html>"""


def shoot(browser, html_text, size, out, tmp):
    src = Path(tmp) / "cover.html"
    src.write_text(html_text, "utf-8")
    out.unlink(missing_ok=True)
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    "--allow-file-access-from-files", f"--user-data-dir={Path(tmp) / 'profile'}",
                    "--force-device-scale-factor=2", f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=5000",
                    f"--screenshot={out}", src.as_uri()], capture_output=True, timeout=120)
    if not out.exists():
        build.fail(f"截图失败：{out}")


def main():
    ap = argparse.ArgumentParser(description="按模板画公众号封面")
    ap.add_argument("articles", nargs="+", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--template")
    args = ap.parse_args()
    browser = find_browser()
    if not browser:
        build.fail("没找到 Chrome / Edge，画不了封面")
    out = args.out or args.articles[0].parent
    out.mkdir(parents=True, exist_ok=True)
    for path in args.articles:
        a, base = build.parse_article(path), path.parent
        tpl = build.load_template(build.find_template(args.template or a["meta"].get("模板") or build.DEFAULT_TEMPLATE, base))
        cover, meta = tpl["cfg"].get("cover"), a["meta"]
        if not cover:
            build.fail(f"模板「{tpl['cfg']['name']}」没有 cover 设置，画不了封面")
        if cover.get("style") != "photo":
            build.fail(f"不认识的封面样式「{cover.get('style')}」，目前只有 photo（清爽实景）")
        parts = [s.strip() for s in (meta.get("封面") or meta["头图"]).split(" / ") if s.strip()]
        head = meta.get("栏目", tpl["cfg"]["series"]) + (f"｜{meta['期数']}" if meta.get("期数") else "")
        tags = " · ".join(t for t in re.split(r"\s*[/、·•・]\s*", meta.get("封面标签", "")) if t)
        texts = (head, "".join(parts[:-1]), re.sub(r"^[（(](.*)[）)]$", r"\1", parts[-1]), tags)
        logo = tpl["dir"] / cover["logo"] if cover.get("logo") else None
        font = find_font(cover, tpl["dir"], base)
        if not font:
            print("提示：没找到思源黑体（Noto Sans SC），改用系统黑体，字会细一些。装好做视频 skill 的引擎后会自动用上。")
        photo = photo_setting(meta, cover, tpl["dir"], base)
        with tempfile.TemporaryDirectory() as tmp:
            wide, square = out / f"封面_{path.stem}.png", out / f"封面_{path.stem}_1比1.png"
            shoot(browser, page(texts, photo, cover, logo, font), (W, H), wide, tmp)
            shoot(browser, page(texts, photo, cover, logo, font, shift=SQ), (H, H), square, tmp)
        print(f"写入 {wide}\n写入 {square}")


if __name__ == "__main__":
    main()
