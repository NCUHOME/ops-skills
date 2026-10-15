#!/usr/bin/env python3
"""公众号封面：按模板 template.json 里的 cover 设置，给每篇文案画一张封面。

用法：
  python3 cover.py 文章.md [更多.md ...] [-o 输出目录] [--template 模板]

每篇输出两张：
  封面_<文件名>.png        2350×1000：上传公众号时，2.35:1 用整张，1:1 框住正中间的正方形
  封面_<文件名>_1比1.png   1000×1000：正中间那块，单独预览或直接用

封面标题取信息区的「封面」（多行用 ` / ` 隔开，例如 南昌大学 / 《学生体质健康标准》 / Q&A / （体质测试篇）），
没有就用「头图」。底部胶囊写「栏目 期数」。需要 Chrome 或 Edge（无头模式截图）。
目前内置的样式：autumn（橙色秋叶，照「教务答疑直通车」往期封面重画）。
"""

import argparse
import base64
import html
import random
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
from thumbnail import find_browser  # noqa: E402

W, H = 1175, 500          # CSS 像素，按 2 倍截图 → 2350×1000
SQ = (W - H) / 2          # 正中正方形的左边界

SHAPES = {
    "maple": "M50 4 L57 23 L67 14 L65 33 L81 24 L75 41 L95 45 L79 55 L87 63 L66 63 L71 77 L55 67 L52 96 "
             "L48 96 L45 67 L29 77 L34 63 L13 63 L21 55 L5 45 L25 41 L19 24 L35 33 L33 14 L43 23 Z",
    "oval": "M50 3 C79 24 83 70 50 97 C17 70 21 24 50 3 Z",
    "ginkgo": "M50 96 L50 64 C28 62 6 44 4 20 C21 30 35 25 50 16 C65 25 79 30 96 20 C94 44 72 62 50 64 Z",
}
VEINS = {
    "maple": "M50 92 L50 22 M50 62 L22 46 M50 62 L78 46 M50 70 L32 70 M50 70 L68 70",
    "oval": "M50 10 L50 92 M50 36 L36 26 M50 36 L64 26 M50 56 L32 44 M50 56 L68 44 M50 74 L36 64 M50 74 L64 64",
    "ginkgo": "M50 94 L50 64 M50 64 L30 30 M50 64 L50 22 M50 64 L70 30",
}
LEAF_COLORS = {"orange": ("#FBB46B", "#EC7A2F"), "red": ("#F79A6A", "#DE5530"), "gold": ("#FFD98A", "#EFAE3C"),
               "light": ("#FFE6B8", "#F6C27A"), "amber": ("#FCC57A", "#E98E37")}


def leaf(x, y, size, shape, color, rot, p="g"):
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot}) scale({size / 100:.3f}) translate(-50 -50)" '
            f'opacity=".95" filter="url(#{p}wc)"><path d="{SHAPES[shape]}" fill="url(#{p}-{color})"/>'
            f'<path d="{VEINS[shape]}" stroke="#FFF3DF" stroke-opacity=".55" stroke-width="2.2" fill="none" '
            f'stroke-linecap="round"/></g>')


def sprig(x, y, length, rot, color="#E8B04A", flip=False, p="g"):
    """金色麦穗枝：一根弯茎，两侧交替长小叶。"""
    s = -1 if flip else 1
    parts = [f'<path d="M0 0 Q {s * 18} {-length * 0.5} {s * 6} {-length}" stroke="{color}" stroke-width="2.4" '
             f'fill="none" stroke-linecap="round"/>']
    n = int(length / 16)
    for i in range(1, n):
        t = i / n
        px, py = s * (2 * (1 - t) * t * 18 + t * t * 6), -length * t
        side = 1 if i % 2 else -1
        sz = 9 + 6 * (1 - abs(t - 0.45))
        parts.append(f'<ellipse cx="{px + side * sz * 0.7:.1f}" cy="{py:.1f}" rx="{sz:.1f}" ry="{sz * 0.38:.1f}" '
                     f'fill="{color}" opacity=".9" transform="rotate({side * -35} {px:.1f} {py:.1f})"/>')
    return f'<g transform="translate({x} {y}) rotate({rot})" filter="url(#{p}wc)">{"".join(parts)}</g>'


def berries(x, y, n, rng, p="g"):
    return "".join(f'<circle cx="{x + rng.uniform(-18, 18):.1f}" cy="{y + rng.uniform(-14, 14):.1f}" '
                   f'r="{rng.uniform(3, 6.5):.1f}" fill="url(#{p}-gold)" opacity=".9"/>' for _ in range(n))


def defs(p):
    grads = "".join(f'<radialGradient id="{p}-{k}" cx="42%" cy="36%" r="72%"><stop offset="0" stop-color="{a}"/>'
                    f'<stop offset="1" stop-color="{b}"/></radialGradient>' for k, (a, b) in LEAF_COLORS.items())
    return (f'<defs>{grads}<filter id="{p}wc" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feTurbulence type="fractalNoise" baseFrequency=".04" numOctaves="3" seed="4" result="n"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="n" scale="4" xChannelSelector="R" yChannelSelector="G"/></filter>'
            f'<filter id="paper"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="2"/>'
            f'<feColorMatrix values="0 0 0 0 .55  0 0 0 0 .35  0 0 0 0 .15  0 0 0 .06 0"/></filter></defs>')


def autumn_decorations():
    """返回 (卡片后面的装饰, 压在卡片上面的装饰)。"""
    rng = random.Random(6)
    top = [(20, 20, 120, "maple", "orange", 18), (115, 5, 90, "oval", "light", -55), (190, 30, 70, "ginkgo", "gold", 20),
           (265, -5, 110, "maple", "red", -12), (905, -4, 112, "maple", "orange", 8), (985, 28, 74, "ginkgo", "gold", -25),
           (1060, 4, 100, "oval", "red", 35), (1150, 30, 120, "maple", "amber", -15),
           (SQ + 18, 8, 112, "maple", "orange", 15), (SQ + 96, -10, 82, "oval", "light", -40),
           (SQ + 62, 74, 56, "ginkgo", "gold", 25), (SQ + 150, -16, 54, "maple", "gold", 30),
           (SQ + H - 18, 14, 108, "maple", "red", -10), (SQ + H - 96, -10, 80, "oval", "amber", 50),
           (SQ + H - 62, 80, 54, "ginkgo", "light", -20), (SQ + H - 150, -14, 52, "oval", "orange", -30),
           (40, 260, 130, "maple", "red", -25), (120, 380, 96, "oval", "gold", 30), (60, 470, 120, "maple", "orange", 15),
           (230, 470, 80, "ginkgo", "light", -10), (1130, 250, 128, "maple", "orange", 20), (1050, 380, 92, "oval", "red", -35),
           (1120, 470, 120, "maple", "gold", -10), (950, 475, 78, "ginkgo", "amber", 15)]
    back = [leaf(*t) for t in top]
    back += [berries(150, 62, 4, rng), berries(1110, 82, 4, rng), berries(SQ + 96, 52, 4, rng), berries(SQ + H - 92, 56, 4, rng)]
    back += [sprig(240, 430, 250, -16), sprig(940, 440, 240, 16, flip=True)]
    front = [sprig(SQ + 60, 440, 220, -8, "#E9B24C", p="f"), sprig(SQ + H - 60, 430, 210, 9, "#E9B24C", flip=True, p="f")]
    front += [leaf(SQ + 50, 466, 92, "maple", "orange", 12, "f"), leaf(SQ + 104, 488, 58, "oval", "gold", -40, "f"),
              leaf(SQ + H - 48, 458, 104, "maple", "red", -15, "f"), leaf(SQ + H - 106, 486, 62, "ginkgo", "light", 20, "f"),
              leaf(SQ + H - 26, 392, 56, "oval", "amber", 30, "f"), leaf(SQ + H - 58, 126, 46, "oval", "light", 35, "f")]
    front += [berries(SQ + 140, 470, 4, rng, "f"), berries(SQ + H - 150, 474, 4, rng, "f")]
    return "\n".join(back), "\n".join(front)


def page(lines, badge, cover, tpl_dir, shift=0):
    """shift>0 时把画面左移、只露出正中的正方形（用来单独截 1:1）。"""
    logo = tpl_dir / cover["logo"]
    logo_uri = "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode() if logo.is_file() else ""
    b, bg = cover["badge"], cover["background"]
    em = max(build.width_em(l) for l in lines)
    fs = min(37, int((H - 100 - 24) / em))  # 最长一行放进卡片
    rows = "".join(f'<div style="font-size: {fs * (0.84 if i == len(lines) - 1 and len(lines) > 2 else 1):.0f}px">'
                   f'{html.escape(l)}</div>' for i, l in enumerate(lines))
    back, front = autumn_decorations()
    width = H if shift else W
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
* {{ margin: 0; box-sizing: border-box; }}
html, body {{ width: {width}px; height: {H}px; overflow: hidden; }}
.canvas {{ position: absolute; left: {-shift}px; top: 0; width: {W}px; height: {H}px;
  background: radial-gradient(ellipse 60% 70% at 50% 55%, {bg[0]} 0%, {bg[1]} 55%, {bg[2]} 100%);
  font-family: "PingFang SC", "Hiragino Sans GB", "Source Han Sans SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }}
svg {{ position: absolute; inset: 0; }}
.logo {{ position: absolute; left: {W / 2 - 135}px; top: 24px; width: 270px; z-index: 3; }}
.front {{ z-index: 2; }}
.card {{ position: absolute; z-index: 1; left: {SQ + 50}px; top: 116px; width: {H - 100}px; height: 352px; border-radius: 18px;
  background: rgba(255, 253, 249, .94); box-shadow: 0 10px 28px rgba(214, 120, 50, .16), 0 0 0 1px rgba(240, 190, 140, .45);
  display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
.title {{ color: {cover["title_color"]}; font-weight: 700; line-height: 1.28; -webkit-text-stroke: .6px {cover["title_color"]}; }}
.badge {{ margin-top: 18px; padding: 7px 24px; border-radius: 999px; font-size: 17px; font-weight: 700; letter-spacing: 3px;
  color: {b["text"]}; background: linear-gradient(90deg, {b["from"]}, {b["to"]}); box-shadow: 0 3px 8px rgba(232, 150, 60, .25); }}
</style></head><body><div class="canvas">
<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">{defs("g")}<rect width="{W}" height="{H}" filter="url(#paper)"/>{back}</svg>
{f'<img class="logo" src="{logo_uri}" alt="logo">' if logo_uri else ''}
<div class="card"><div class="title">{rows}</div><div class="badge">{html.escape(badge)}</div></div>
<svg class="front" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{defs("f")}{front}</svg>
</div></body></html>"""


def shoot(browser, html_text, size, out, tmp):
    src = Path(tmp) / "cover.html"
    src.write_text(html_text, "utf-8")
    out.unlink(missing_ok=True)
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    f"--user-data-dir={Path(tmp) / 'profile'}", "--force-device-scale-factor=2",
                    f"--window-size={size[0]},{size[1]}", f"--screenshot={out}", src.as_uri()],
                   capture_output=True, timeout=120)
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
        a = build.parse_article(path)
        tpl = build.load_template(build.find_template(args.template or a["meta"].get("模板") or build.DEFAULT_TEMPLATE,
                                                      path.parent))
        cover = tpl["cfg"].get("cover")
        if not cover:
            build.fail(f"模板「{tpl['cfg']['name']}」没有 cover 设置，画不了封面")
        lines = [s.strip() for s in (a["meta"].get("封面") or a["meta"]["头图"]).split(" / ") if s.strip()]
        badge = f"{a['meta'].get('栏目', tpl['cfg']['series'])}　{a['meta'].get('期数', '')}".strip()
        with tempfile.TemporaryDirectory() as tmp:
            wide, square = out / f"封面_{path.stem}.png", out / f"封面_{path.stem}_1比1.png"
            shoot(browser, page(lines, badge, cover, tpl["dir"]), (W, H), wide, tmp)
            shoot(browser, page(lines, badge, cover, tpl["dir"], shift=SQ), (H, H), square, tmp)
        print(f"写入 {wide}\n写入 {square}")


if __name__ == "__main__":
    main()
