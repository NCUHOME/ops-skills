#!/usr/bin/env python3
"""从公众号文章链接取正文代码，作为复刻新版式的参考。

用法：
  python3 fetch_article.py "https://mp.weixin.qq.com/s/xxxx" -o 参考.html

输出的 参考.html 只含正文节点（#js_content）的内容，图片保留 data-src；同时打印文章标题和公众号名。
取不到时（链接失效、触发验证页），改用浏览器打开文章 → 开发者工具 → 复制 #js_content 的 outerHTML。
"""

import argparse
import html
import re
import sys
import urllib.request
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


class InnerHTML(HTMLParser):
    """找到 id=js_content 的元素，按标签嵌套原样取回它的内部代码。"""

    VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "embed", "param", "track"}

    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        # getpos() 只按 \n 计行，行首偏移也只按 \n 算
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", src)]
        self.start = self.end = None
        self.depth = 0

    def abs_pos(self):  # 不能叫 offset：HTMLParser 自己有同名属性
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if self.end is not None:
            return
        if self.start is None:
            if dict(attrs).get("id") == "js_content":
                self.start = self.abs_pos() + len(self.get_starttag_text())
                self.depth = 1
            return
        if tag not in self.VOID:
            self.depth += 1

    def handle_endtag(self, tag):
        if self.start is None or self.end is not None or tag in self.VOID:
            return
        self.depth -= 1
        if self.depth == 0:
            self.end = self.abs_pos()


def main():
    ap = argparse.ArgumentParser(description="从公众号文章链接取正文代码")
    ap.add_argument("url")
    ap.add_argument("-o", "--out", default="参考.html")
    args = ap.parse_args()
    if not re.match(r"https?://mp\.weixin\.qq\.com/", args.url):
        sys.exit("✗ 只支持 mp.weixin.qq.com 的文章链接")

    req = urllib.request.Request(args.url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=20) as r:
        src = r.read().decode("utf-8", errors="replace")

    p = InnerHTML(src)
    p.feed(src)
    if p.start is None or p.end is None:
        sys.exit("✗ 页面里没有找到正文（可能触发了验证页或文章已删除）。请用浏览器打开文章，"
                 "在开发者工具里复制 #js_content 的 outerHTML。")
    body = src[p.start:p.end].strip()

    def meta(prop):
        m = re.search(rf'<meta property="{prop}" content="([^"]*)"', src)
        return html.unescape(m.group(1)) if m else ""

    title = meta("og:title")
    account = re.search(r'<strong class="profile_nickname"[^>]*>([^<]+)</strong>', src) or \
        re.search(r'var nickname = htmlDecode\("([^"]*)"\)', src)
    account = html.unescape(account.group(1).strip()) if account else ""
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"<!-- 来源：{title}｜{account}｜{args.url} -->\n{body}\n")
    print(f"标题：{title}\n公众号：{account}\n正文 {len(body):,} 字符 → {args.out}")


if __name__ == "__main__":
    main()
