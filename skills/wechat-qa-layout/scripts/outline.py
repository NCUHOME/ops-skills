#!/usr/bin/env python3
"""拆解一篇参考推文的代码：输出缩进大纲（标签、关键样式、文字、图片），用来照着复刻新版式。

用法：
  python3 outline.py 参考推文.html            # 大纲
  python3 outline.py 参考推文.html --images   # 只列出全部图片链接（去重，按出现顺序）

参考推文代码的拿法见 references/NEW-LAYOUT.md。公众号视频播放器那一大段（class 含 video_iframe）会折叠成一行。
"""

import argparse
import html
import re
import sys
from html.parser import HTMLParser

VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr"}
NOISE = {"visibility", "box-sizing", "pointer-events", "-webkit-tap-highlight-color"}


def short_style(style):
    keep = []
    for decl in style.split(";"):
        decl = decl.strip()
        if decl and decl.split(":", 1)[0].strip() not in NOISE:
            keep.append(decl)
    return "; ".join(keep)


class Outline(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth, self.rows, self.skip, self.images = 0, [], 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.skip:
            if tag not in VOID:
                self.skip += 1
            return
        pad = "  " * self.depth
        if "video_iframe" in a.get("class", ""):
            self.rows.append(f"{pad}[视频播放器]（复刻时换成占位框）")
            self.skip = 1
            return
        # 导出的代码是渲染后的：图片真正的样式在 data-original-style 里
        style = a.get("data-original-style") or a.get("style", "")
        line = f"{pad}<{tag}> {short_style(style)}"
        if tag == "img":
            src = html.unescape(a.get("data-src") or a.get("src", ""))
            src = re.sub(r"#imgIndex=\d+$", "", src)
            if src and src not in self.images:
                self.images.append(src)
            line += f"  IMG#{self.images.index(src) + 1 if src in self.images else '?'} 宽高比={a.get('data-ratio', '?')}"
        if tag == "svg" and a.get("viewbox"):
            line += f"  viewBox={a['viewbox']}"
        if tag == "svg" and a.get("y"):
            line += f"  x={a.get('x')} y={a.get('y')} w={a.get('width')} h={a.get('height')}"
        self.rows.append(line)
        if tag not in VOID:
            self.depth += 1

    def handle_endtag(self, tag):
        if self.skip:
            if tag not in VOID:
                self.skip -= 1
            return
        if tag not in VOID:
            self.depth = max(0, self.depth - 1)

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.rows.append("  " * self.depth + "「" + data.strip() + "」")


def main():
    ap = argparse.ArgumentParser(description="拆解参考推文代码的结构")
    ap.add_argument("file", help="参考推文的 HTML（正文节点的 outerHTML 或导出的文章代码）")
    ap.add_argument("--images", action="store_true", help="只列出图片链接")
    args = ap.parse_args()
    o = Outline()
    o.feed(open(args.file, encoding="utf-8").read())
    if args.images:
        for i, u in enumerate(o.images, 1):
            print(f"IMG#{i}  {u}")
    else:
        sys.stdout.write("\n".join(o.rows) + "\n")


if __name__ == "__main__":
    main()
