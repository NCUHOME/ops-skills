#!/usr/bin/env python3
"""给模板生成缩略图 preview.png：用模板自己的 example.md 生成手机预览，再用无头 Chrome / Edge 截图。

用法：
  python3 thumbnail.py <模板名或模板文件夹>

截的是 375px 宽手机上文章的开头（头图和第一个分区），2 倍清晰度。没有找到 Chrome / Edge 时，
手动截一张同样范围的图，存成模板文件夹里的 preview.png 即可。
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
]


def find_browser():
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        if shutil.which(name):
            return shutil.which(name)
    return next((b for b in BROWSERS if Path(b).is_file()), None)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = build.find_template(sys.argv[1])
    a = build.parse_article(folder / "example.md")
    build.use_template(build.load_template(folder))
    a["meta"].pop("视频", None)  # 缩略图只看模板自己的样子，不放视频占位
    body = build.COMP["article_html"](a, True).render(pretty=False)
    css = re.search(r"<style>(.*?)</style>", build.PREVIEW, re.S).group(1)
    page = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer">'
            f'<style>{css} body {{ background: #fff; }}</style></head><body><div class="rich_media_area_primary" '
            f'style="width: 375px;"><div class="rich_media_content">{body}</div></div></body></html>')

    browser = find_browser()
    if not browser:
        sys.exit("✗ 没找到 Chrome / Edge。请手动截一张 375px 宽手机上文章开头的图，存成 "
                 f"{folder / 'preview.png'}")
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "page.html"
        html_path.write_text(page, encoding="utf-8")
        out = folder / "preview.png"
        out.unlink(missing_ok=True)  # 截图失败时不留旧图冒充
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                        f"--user-data-dir={Path(tmp) / 'profile'}", "--force-device-scale-factor=2",
                        "--window-size=375,720", "--virtual-time-budget=10000",
                        f"--screenshot={out}", html_path.as_uri()], capture_output=True, timeout=120)
    if not out.exists():
        sys.exit("✗ 截图失败，请手动截图（见本脚本说明）")
    print(f"写入 {out}")


if __name__ == "__main__":
    main()
