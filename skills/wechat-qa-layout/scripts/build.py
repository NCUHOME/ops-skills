#!/usr/bin/env python3
"""问答文案（Markdown）→ 公众号推文排版代码 + 手机预览页。

用法：
  python3 build.py 文章.md [更多.md ...] [-o 输出目录] [--template 模板] [--check]

  -o / --out   输出目录，默认与第一篇 .md 相同
  --template   模板：templates/ 下的模板名（如 jwdy），或模板文件夹路径。
               不写就用文案信息区里的「模板」，再没有就用 jwdy
  --check      只检查排版规范（问题最多两行等），不生成文件；有问题时退出码为 1

输出：
  <文件名>.html   每篇一个，粘贴进公众号编辑器的正文代码（只有行内样式，公众号能保留）
  预览.html       手机宽度预览、一键复制、四种屏宽自动自检

一个模板是一个文件夹：template.json（颜色、图片、头图叠层、字数限制）＋ 可选的 components.py
（结构和默认不同时，覆盖下面 DEFAULT 里的构件函数）。见 references/NEW-LAYOUT.md。
文案写法见 references/FORMAT.md。只用 Python 标准库；装了 ffmpeg 时会自动读取视频时长、截封面帧。
"""

import argparse
import base64
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # 载入模板的 components.py 时，不在模板文件夹里留 __pycache__
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
DEFAULT_TEMPLATE = "jwdy"
BB = "box-sizing: border-box;"
T = {}     # 当前模板的配置（template.json）
COMP = {}  # 当前模板的构件函数：默认实现 + components.py 的覆盖


def fail(msg):
    sys.exit(f"✗ {msg}")


# ───────────────────────────── 模板 ─────────────────────────────

def list_templates():
    """模板库里的全部模板，按 order 排序：[(模板名, 配置)]"""
    out = []
    for d in TEMPLATES.iterdir():
        if (d / "template.json").is_file():
            out.append((d.name, json.loads((d / "template.json").read_text(encoding="utf-8"))))
    return sorted(out, key=lambda x: (x[1].get("order", 999), x[0]))


def find_template(spec, base=Path(".")):
    """模板名或路径 → 模板文件夹。路径可以相对当前目录或文案所在目录。"""
    for cand in (Path(spec), base / spec):
        if (cand / "template.json").is_file():
            return cand.resolve()
    if (TEMPLATES / spec / "template.json").is_file():
        return TEMPLATES / spec
    fail(f"找不到模板「{spec}」。模板库里有：{'、'.join(n for n, _ in list_templates())}")


_loaded = {}


def load_template(folder):
    folder = Path(folder).resolve()
    if folder not in _loaded:
        cfg = json.loads((folder / "template.json").read_text(encoding="utf-8"))
        comps = {}
        py = folder / "components.py"
        if py.is_file():
            spec = importlib.util.spec_from_file_location(f"template_{folder.name}", py)
            mod = importlib.util.module_from_spec(spec)
            mod.__dict__.update(API)  # 构件里可以直接用 E、P、rich、img、T、DEFAULT 等
            spec.loader.exec_module(mod)
            comps = {k: getattr(mod, k) for k in DEFAULT if callable(getattr(mod, k, None))}
        _loaded[folder] = {"id": folder.name, "dir": folder, "cfg": cfg, "comps": comps}
    return _loaded[folder]


def use_template(tpl):
    T.clear()
    T.update(tpl["cfg"])
    COMP.clear()
    COMP.update(DEFAULT)
    COMP.update(tpl["comps"])


# ───────────────────────────── 文案解析 ─────────────────────────────

def parse_article(path):
    """读一篇文案 .md → {meta, sections:[{title, paras, qas:[{q:[行], a:[段]}]}], tip:[行]|None}"""
    src = path.read_text(encoding="utf-8-sig")
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    meta = {}
    m = re.match(r"\s*---[ \t]*\n(.*?)\n---[ \t]*\n", src, re.S)
    if m:
        for line in m.group(1).splitlines():
            kv = re.split(r"\s*[:：]\s*", line.strip(), maxsplit=1)
            if len(kv) == 2 and kv[0]:
                meta[kv[0]] = kv[1]
        src = src[m.end():]
    for key in ("标题", "头图"):
        if not meta.get(key):
            fail(f"{path.name}：开头 --- 信息区缺少「{key}」")

    sections, tip, summary = [], None, None
    sec = target = None
    cont = False  # 上一行以 \ 结尾：本行并入同一段
    for no, raw in enumerate(src.splitlines(), 1):
        line = raw.strip()
        if not line:
            cont = False
            continue
        if line.startswith("## "):
            name = line[3:].strip()
            if name == "温馨提示":
                tip, sec = [], None
                target = tip
            elif name in ("最后再次划重点", "划重点"):
                summary, sec = [], None
                target = summary
            else:
                sec = {"title": name, "paras": [], "qas": []}
                sections.append(sec)
                target = sec["paras"]
            cont = False
            continue
        if line.startswith("### "):
            if sec is None:
                fail(f"{path.name} 第 {no} 行：问题前要先有「## 分区标题」")
            qa = {"q": [s.strip() for s in line[4:].split(" / ") if s.strip()], "a": []}
            sec["qas"].append(qa)
            target, cont = qa["a"], False
            continue
        if line.startswith("#"):
            fail(f"{path.name} 第 {no} 行：只支持「## 分区」「### 问题」两级标题")
        if target is None:
            fail(f"{path.name} 第 {no} 行：正文前要先有「## 分区标题」")
        hard = line.endswith("\\")
        text = line[:-1].rstrip() if hard else line
        if cont and target:
            target[-1] += "\n" + text
        else:
            target.append(text)
        cont = hard
    if not sections:
        fail(f"{path.name}：没有任何「## 分区」")
    return {"path": path, "meta": meta, "sections": sections, "tip": tip, "summary": summary}


def width_em(s):
    """估算显示宽度（字）：汉字和全角符号算 1，半角字母数字算 0.72（按粗体实测）。"""
    s = re.sub(r"\*\*|`", "", s)
    return sum(1 if ord(ch) > 0x2E80 else 0.72 for ch in s)


def lint(a):
    """排版硬性要求（见 SKILL.md），限制值取自当前模板。返回问题列表，空表示合规。"""
    L, out = T["limits"], []
    head = a["meta"]["头图"].split(" / ")
    if len(head) > L["header_lines"]:
        out.append(f"头图标题超过 {L['header_lines']} 行：{a['meta']['头图']}")
    for sec in a["sections"]:
        if width_em(sec["title"]) > L["section_title_chars"]:
            out.append(f"分区标题超过 {L['section_title_chars']} 字（窄屏会撑出）：{sec['title']}")
        if not sec["qas"] and not sec["paras"]:
            out.append(f"分区是空的：{sec['title']}")
        for qa in sec["qas"]:
            q = " / ".join(qa["q"])
            if len(qa["q"]) > L["question_lines"]:
                out.append(f"问题超过 {L['question_lines']} 行（三四行很丑，请精简后再分行）：{q}")
            for line in qa["q"]:
                if width_em(line) > L["question_line_chars"]:
                    out.append(f"问题单行超过 {L['question_line_chars']} 字（360px 手机会折行）：{line}")
            if not qa["a"]:
                out.append(f"问题没有答案：{q}")
    texts = ([p for s in a["sections"] for p in s["paras"] + [x for qa in s["qas"] for x in qa["a"]]]
             + (a["tip"] or []) + (a["summary"] or []))
    for t in texts:
        if t.count("**") % 2 or t.count("`") % 2:
            out.append(f"加粗 ** 或反引号 ` 没有成对：{t[:30]}…")
    return out


# ───────────────────────────── 视频信息 ─────────────────────────────

def video_info(a):
    """返回 (文件名, 时长, 封面帧 data URI)。视频文件存在且装了 ffmpeg 时自动读取。"""
    if "_video" not in a:
        a["_video"] = _probe_video(a)
    return a["_video"]


def _probe_video(a):
    meta, base = a["meta"], a["path"].parent
    name = meta.get("视频", "")
    vpath = (base / name) if name else None
    length, poster = meta.get("时长", ""), ""
    if meta.get("封面帧"):
        p = base / meta["封面帧"]
        if p.exists():
            mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            poster = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    if vpath and vpath.is_file():
        if not length and shutil.which("ffprobe"):
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(vpath)],
                               capture_output=True, text=True)
            try:
                sec = round(float(r.stdout.strip()))
                length = f"{sec // 60:02d}:{sec % 60:02d}"
            except ValueError:
                pass
        if not poster and shutil.which("ffmpeg"):
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "poster.jpg"
                subprocess.run(["ffmpeg", "-v", "error", "-ss", "1.5", "-i", str(vpath), "-frames:v", "1",
                                "-vf", "scale=960:-2", "-q:v", "4", str(out), "-y"], capture_output=True)
                if out.exists():
                    poster = "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()
    return Path(name).name, length, poster


# ───────────────────────────── 构件 ─────────────────────────────

class E:
    """极简 DOM：块级元素换行缩进；含文字的元素（inline=True）整行输出，避免引入多余空格。"""

    def __init__(self, tag, style=None, *children, attrs=None, inline=False):
        self.tag, self.style, self.children = tag, style, children
        self.attrs, self.inline = attrs or {}, inline

    def open(self):
        a = "".join(f' {k}="{v}"' for k, v in self.attrs.items())
        s = f' style="{self.style}"' if self.style else ""
        return f"<{self.tag}{a}{s}>"

    def render(self, pretty=True, depth=0):
        pad = "  " * depth if pretty else ""
        if self.tag == "img":
            return pad + self.open()
        if self.inline or not pretty:
            inner = "".join(c if isinstance(c, str) else c.render(False) for c in self.children)
            return f"{pad}{self.open()}{inner}</{self.tag}>"
        rows = [pad + self.open()]
        rows += [c.render(True, depth + 1) if isinstance(c, E) else "  " * (depth + 1) + c for c in self.children]
        rows.append(f"{pad}</{self.tag}>")
        return "\n".join(rows)


def rich(text):
    """转义；**加粗**；`收紧字距`；\\n 段内换行。"""
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", rf'<strong style="{BB}">\1</strong>', t)
    t = re.sub(r"`(.+?)`", rf'<span style="letter-spacing: 1.5px; {BB}">\1</span>', t)
    return t.replace("\n", "<br>")


def P(style, text):
    return E("p", style, rich(text), inline=True)


def chk(pv, kind):
    """预览版给构件打标记，供预览页自检定位；粘贴版不带。kind：q 问题框 / title 分区标题 / ans 答案。"""
    return {"data-chk": kind} if pv else None


def img(key, extra=""):
    url = T["images"][key]
    cls = "rich_pages wxw-img" + (" __bg_gif" if "gif" in url else "")
    return E("img", None, attrs={"src": url, "class": cls, "width": "100%", "alt": "Image",
                                 "style": f"vertical-align: middle; max-width: 100%; width: 100%; {extra}{BB}"})


def header_layer(w, h, ml, mt, fs, key):
    return E("section", f"width: {w}%; height: {h}%; transform: rotate(0deg); margin-left: {ml}%; "
                        f"margin-top: {mt}%; grid-column-start: 1; grid-row-start: 1; {BB}",
             E("section", f"text-align: center; line-height: 0; font-size: {fs}px; height: 100%; pointer-events: none; {BB}",
               E("section", f"max-width: 100%; vertical-align: middle; display: inline-block; line-height: 0; "
                            f"width: 100%; pointer-events: none; {BB}",
                 img(key, "height: auto; "))))


def svg_text_layer(y, h, text_style, *paras):
    vw, vh = T["header"]["viewbox"]
    return E("section", f"grid-column-start: 1; grid-row-start: 1; display: flex; pointer-events: none; {BB}",
             E("svg", f"transform: rotate(0deg); {BB}",
               E("svg", f"overflow: initial; {BB}",
                 E("foreignObject", f"transform-origin: center center; transform: rotate(0deg); {BB}",
                   E("section", f"height: 100%; {BB}", E("section", text_style, *paras)),
                   attrs={"width": "100%", "height": "100%"}),
                 attrs={"width": "90%", "height": f"{h:.4f}%", "x": "5%", "y": f"{y:.4f}%"}),
               attrs={"xmlns": "http://www.w3.org/2000/svg", "width": "100%", "height": "100%",
                      "viewBox": f"0 0 {vw} {vh}"}))


def br():
    return E("p", f"white-space: normal; margin: 0px; padding: 0px; {BB}", "<br>", inline=True)


def header(a):
    H, C = T["header"], T["colors"]
    vw, vh = H["viewbox"]
    box = H["title_box"]
    lines = [s.strip() for s in a["meta"]["头图"].split(" / ") if s.strip()]
    lh = 1.4 if len(lines) <= 2 else 1.3  # 三行时收紧行高，放进同一个标题框
    by_width = vw * box["width_ratio"] / max(width_em(l) for l in lines)
    by_height = box["height"] / 100 * vh / (len(lines) * lh)
    fs = min(box["max_font"], round(by_width), round(by_height))
    h = len(lines) * fs * lh / vh * 100
    y = box["y"] + (box["height"] - h) / 2  # 在标题框内垂直居中
    ps = f"margin: 0px; padding: 0px; {BB}"
    title = svg_text_layer(y, h, f"font-size: {fs}px; color: {C['main']}; text-align: center; word-break: break-word; "
                                 f"line-height: {lh}; {BB}", *[P(ps, f"**{l}**") for l in lines])
    series = a["meta"].get("栏目", T["series"])
    episode = a["meta"].get("期数", "")
    sb = H["subtitle_box"]
    sub = svg_text_layer(sb["y"], sb["height"], f"font-size: {sb['font']}px; color: {C['subtitle']}; text-align: center; "
                                                f"letter-spacing: 1px; word-break: break-word; {BB}",
                         P(ps, f"**- {series} {episode} -**".replace("  ", " ")))
    spacer = E("section", f"grid-column-start: 1; grid-row-start: 1; padding-top: {H['padding_top']}; {BB}",
               E("svg", "float: left; line-height: 0; width: 0px; vertical-align: top;", attrs={"viewBox": "0 0 1 1"}))
    return E("section", f"display: grid; width: 100%; overflow: hidden; align-self: flex-start; "
                        f"background-color: {C['header_bg']}; line-height: 1.6; letter-spacing: 0px; color: rgb(0, 0, 0); "
                        f"aspect-ratio: {H['aspect_ratio']}; grid-template-columns: 100%; grid-template-rows: 100%; {BB}",
             *[header_layer(*l) for l in H["back_layers"]], title, sub,
             *[header_layer(*l) for l in H["front_layers"]], spacer)


def video_blocks(a, pv):
    if not a["meta"].get("视频"):
        return []
    C = T["colors"]
    name, length, poster = video_info(a)
    hint = E("section", f"text-align: center; justify-content: center; display: flex; flex-flow: row; {BB}",
             E("section", f"display: inline-block; width: 90%; vertical-align: top; align-self: flex-start; flex: 0 0 auto; "
                          f"background-color: {C['hint_bg']}; height: auto; padding: 1px 0px 1px 14px; "
                          f"border-radius: 5px; overflow: hidden; {BB}",
               E("section", f"color: {C['main']}; letter-spacing: 1px; font-size: 14px; {BB}",
                 P(f"margin: 0px; padding: 0px; {BB}", f"**{a['meta'].get('视频提示', T['video_hint'])}**"))))
    return [hint, br(), COMP["video_slot"](a, pv, name, length, poster), br()]


def video_slot(a, pv, name, length, poster):
    """视频位置。预览页：仿公众号播放器；粘贴版：占位框，进编辑器后在此插入视频并删掉。各模板通用，一般不用覆盖。"""
    if pv:
        return E("section", None, E("div", None, attrs={
            "class": "mock-video", "data-len": length, "style": f"background-image: url('{poster}');" if poster else ""}))
    C = T["colors"]
    grey = f"margin: 0px; padding: 0px; color: rgb(153, 153, 153); font-size: 12px; {BB}"
    return E("section", f"border: 2px dashed {C['accent']}; background-color: rgb(255, 255, 255); padding: 36px 12px; "
                        f"text-align: center; {BB}",
             P(f"margin: 0px; padding: 0px; color: {C['main']}; font-size: 15px; letter-spacing: 1px; {BB}",
               "**▶ 在此插入视频（插入后删除本框）**"),
             P(grey.replace("margin: 0px", "margin: 6px 0px 0px"), f"{a['meta']['标题']}　{length}".strip()),
             *([P(grey, name)] if name else []))


def section_title(text, pv):
    C, D = T["colors"], T["section_deco"]

    def deco(key, width, margin):
        return E("section", f"display: flex; width: 100%; flex-flow: column; {BB}",
                 E("section", f"z-index: 2; {BB}",
                   E("section", f"margin: {margin}; line-height: 0; {BB}",
                     E("section", f"max-width: 100%; vertical-align: middle; display: inline-block; line-height: 0; "
                                  f"width: {width}; height: auto; {BB}", img(key)))))

    return E("section", f"text-align: center; justify-content: center; display: flex; flex-flow: row; margin: 50px 0px 15px; {BB}",
             E("section", f"display: inline-block; width: auto; vertical-align: top; align-self: flex-start; flex: 0 0 auto; "
                          f"min-width: 5%; max-width: 100%; height: auto; {BB}",
               E("section", f"justify-content: center; display: flex; flex-flow: row; {BB}",
                 E("section", f"display: inline-block; vertical-align: bottom; width: auto; align-self: flex-end; flex: 0 0 auto; "
                              f"min-width: 5%; max-width: 100%; height: auto; margin: 0px 0px 0px -28px; {BB}",
                   deco(D["left"], "60px", "0px")),
                 E("section", f"display: inline-block; vertical-align: top; width: auto; align-self: flex-start; flex: 0 0 auto; "
                              f"background-color: {C['main']}; padding: 5px 30px; min-width: 5%; max-width: 100%; height: auto; "
                              f"margin: 0px -18px 0px -20px; {BB}",
                   E("section", f"text-align: justify; font-size: 15px; color: rgb(255, 255, 255); letter-spacing: 1px; {BB}",
                     P(f"white-space: normal; margin: 0px; padding: 0px; {BB}", f"**{text}**"))),
                 E("section", f"display: inline-block; vertical-align: top; width: auto; align-self: flex-start; flex: 0 0 auto; "
                              f"min-width: 5%; max-width: 100%; height: auto; {BB}",
                   deco(D["right"], "30px", "-10px 0px 0px"))),
               attrs=chk(pv, "title")))


def question(n, lines, first, pv):
    C = T["colors"]
    badge = E("section", f"display: inline-block; vertical-align: middle; width: auto; align-self: center; flex: 0 0 auto; "
                         f"min-width: 5%; max-width: 100%; height: auto; {BB}",
              E("section", f"text-align: center; {BB}",
                E("section", f"display: inline-block; width: 29px; height: 29px; vertical-align: top; overflow: hidden; "
                             f"border-radius: 275px; background-color: {C['accent']}; {BB}",
                  E("section", f"margin: 2px 0px 0px; {BB}",
                    E("section", f"color: rgb(255, 255, 255); {BB}",
                      P(f"margin: 0px; padding: 0px; {BB}", f"**{n:02d}**"))))))
    # flex-shrink 为 1（参考推文是 0）：问题过长时在框内换行，而不是撑出卡片
    box = E("section", f"display: inline-block; vertical-align: top; width: auto; align-self: flex-start; flex: 0 1 auto; "
                       f"border-style: dashed; border-width: 1px 0px; border-top-color: {C['accent']}; "
                       f"border-bottom-color: {C['accent']}; padding: 1px 10px; min-width: 5%; max-width: 100%; height: auto; {BB}",
            E("section", f"text-align: justify; color: {C['main']}; letter-spacing: 1px; {BB}",
              *[P(f"white-space: normal; margin: 0px; padding: 0px; {BB}", f"**{l}**") for l in lines]),
            attrs=chk(pv, "q"))
    margin = "0px 0px 12px" if first else "25px 0px 12px"
    return E("section", f"text-align: left; justify-content: flex-start; display: flex; flex-flow: row; margin: {margin}; {BB}",
             badge, box)


def paragraphs(paras, indent, pv):
    def para(t):
        # 两端对齐时，换不了行的长串（QQ 号、网址）会把上一行撑出大空隙：这类段落允许断在串中间
        brk = "word-break: break-all; " if re.search(r"\d{6,}|https?://", t) else ""
        t = re.sub(r"(?<=\d)/(?=\d)", "/​", t)  # “800/1000” 允许在斜杠后断行
        return P(f"text-indent: {indent}; {brk}white-space: normal; margin: 0px; padding: 0px; {BB}", t)
    return E("section", f"text-align: justify; font-size: 14px; line-height: 1.85; letter-spacing: 2.8px; {BB}",
             *[para(t) for t in paras], attrs=chk(pv, "ans"))


def card(sec, pv):
    body = [COMP["paragraphs"](sec["paras"], "2em", pv)] if sec["paras"] else []
    for i, qa in enumerate(sec["qas"]):
        body += [COMP["question"](i + 1, qa["q"], i == 0 and not body, pv), COMP["paragraphs"](qa["a"], "2.4em", pv)]
    return E("section", f"text-align: center; justify-content: center; display: flex; flex-flow: row; {BB}",
             E("section", f"display: inline-block; width: 90%; vertical-align: top; align-self: flex-start; flex: 0 0 auto; "
                          f"height: auto; border-style: solid; border-width: 1px; border-color: {T['colors']['card_border']}; "
                          f"background-color: rgb(255, 255, 255); padding: 20px 18px; {BB}", *body))


def tip(lines):
    ps = f"text-align: center; white-space: normal; margin: 0px; padding: 0px; {BB} line-height: 1.75em;"
    return E("section", BB, br(), *[E("p", ps, f'<span style="font-size: 14px; {BB}">{rich(l)}</span>', inline=True)
                                    for l in [T["tip_heading"]] + lines])


def summary(paras, pv):
    """结尾「最后再次划重点」总结框：浅色外框 + 白底细边内框，字号与答案一致。"""
    C = T["colors"]
    ps = f"text-indent: 2em; white-space: normal; margin: 0px; padding: 0px; {BB}"
    return E("section", f"text-align: center; justify-content: center; display: flex; flex-flow: row; margin: 40px 0px 0px; {BB}",
             E("section", f"display: inline-block; width: 90%; vertical-align: top; align-self: flex-start; flex: 0 0 auto; "
                          f"background-color: {C['hint_bg']}; padding: 6px; {BB}",
               E("section", f"border: 1px solid {C['card_border']}; background-color: rgb(255, 255, 255); "
                            f"padding: 18px 16px; text-align: justify; {BB}",
                 P(f"margin: 0px 0px 6px; padding: 0px; color: {C['main']}; font-size: 15px; letter-spacing: 1px; {BB}",
                   T.get("summary_heading", "💡**最后再次划重点：**")),
                 E("section", f"font-size: 14px; line-height: 1.85; letter-spacing: 2px; {BB}",
                   *[P(ps, t) for t in paras], attrs=chk(pv, "ans")))))


def article_html(a, pv=False):
    C = T["colors"]
    blocks = [COMP["header"](a), *COMP["video_blocks"](a, pv)]
    for sec in a["sections"]:
        blocks += [COMP["section_title"](sec["title"], pv), COMP["card"](sec, pv)]
    if a["summary"]:
        blocks.append(COMP["summary"](a["summary"], pv))
    if a["tip"]:
        blocks.append(COMP["tip"](a["tip"]))
    blocks.append(br())
    return E("section", f"background-color: {C['page_bg']}; {BB} font-style: normal; font-weight: 400; "
                        f"text-align: justify; font-size: 16px; color: {C['text']};", *blocks)


# 模板的 components.py 可以覆盖其中任意几个（同名函数）；没覆盖的用默认实现
DEFAULT = {f.__name__: f for f in (header, video_blocks, video_slot, section_title, question,
                                   paragraphs, card, summary, tip, article_html)}
# components.py 里可直接使用的名字
API = {"E": E, "P": P, "rich": rich, "img": img, "br": br, "chk": chk, "BB": BB, "T": T, "COMP": COMP,
       "DEFAULT": DEFAULT, "header_layer": header_layer, "svg_text_layer": svg_text_layer,
       "video_info": video_info, "width_em": width_em, "re": re}


def plain_text(a):
    clean = lambda s: re.sub(r"\*\*|`", "", s)
    out = [a["meta"]["标题"], ""]
    for sec in a["sections"]:
        out.append(f"【{sec['title']}】")
        out += [clean(p) for p in sec["paras"]]
        for i, qa in enumerate(sec["qas"]):
            out.append(f"{i + 1:02d} {''.join(qa['q'])}")
            out += [clean(p) for p in qa["a"]]
        out.append("")
    if a["summary"]:
        out += ["最后再次划重点："] + [clean(p) for p in a["summary"]]
    out += [clean(l) for l in (a["tip"] or [])]
    return "\n".join(out)


def render_article(path, template=None):
    """读文案、选模板、生成。返回 {a, tpl, lint, code（粘贴版，缩进）, code_min（粘贴版，一行）, preview}。"""
    a = parse_article(Path(path))
    spec = template or a["meta"].get("模板") or DEFAULT_TEMPLATE
    tpl = load_template(find_template(spec, a["path"].parent))
    use_template(tpl)
    return {"a": a, "tpl": tpl, "lint": lint(a),
            "code": COMP["article_html"](a).render(pretty=True),
            "code_min": COMP["article_html"](a).render(pretty=False),
            "preview": COMP["article_html"](a, True).render(pretty=False)}


# ───────────────────────────── 输出 ─────────────────────────────

def main():
    for stream in (sys.stdout, sys.stderr):  # Windows 控制台编码打不出 ⚠️ 时不至于报错
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="问答文案 .md → 公众号推文排版代码 + 预览页")
    ap.add_argument("articles", nargs="+", type=Path, help="文案 .md 文件")
    ap.add_argument("-o", "--out", type=Path, help="输出目录（默认与第一篇 .md 相同）")
    ap.add_argument("--template", help="模板名或模板文件夹（默认看文案信息区的「模板」，再没有用 jwdy）")
    ap.add_argument("--check", action="store_true", help="只检查排版规范，不生成文件")
    args = ap.parse_args()

    results = [render_article(p, args.template) for p in args.articles]
    problems = 0
    for r in results:
        for w in r["lint"]:
            print(f"⚠️  {r['a']['path'].name}｜{w}")
            problems += 1
    if args.check:
        print("✓ 排版规范检查通过" if not problems else f"共 {problems} 处不合规")
        sys.exit(1 if problems else 0)

    out = args.out or results[0]["a"]["path"].parent
    out.mkdir(parents=True, exist_ok=True)
    payload = []
    for r in results:
        a, cfg = r["a"], r["tpl"]["cfg"]
        name = a["meta"].get("视频", "")
        head = f"<!-- {a['meta']['标题']}｜模板：{cfg['name']}"
        head += f"\n     粘贴后在黄色虚线框处插入视频（{Path(name).name}）并删掉虚线框 -->\n" if name else " -->\n"
        target = out / f"{a['path'].stem}.html"
        target.write_text(head + r["code"] + "\n", encoding="utf-8")
        print(f"写入 {target}")
        payload.append({
            "name": a["path"].stem,
            "template": cfg["name"],
            "account": cfg.get("account", ""),
            "title": a["meta"]["标题"],
            "html": r["code_min"],  # 复制用：压成一行
            "text": plain_text(a),
            "preview": r["preview"],
            "lint": r["lint"],
        })
    page = PREVIEW.replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    (out / "预览.html").write_text(page, encoding="utf-8")
    print(f"写入 {out / '预览.html'}" + ("" if not problems else f"（有 {problems} 处不合规，见上方 ⚠️）"))


PREVIEW = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>推文排版预览</title>
<style>
:root {
  --page: #edf1ed; --ink: #1f2a21; --muted: #667168; --line: #d5ddd5;
  --green: rgb(67, 156, 75); --warn: #b45309; --phone: 390px;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 14px/1.6 -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; }
.top { max-width: 1100px; margin: 0 auto; padding: 28px 16px 4px; display: flex; flex-wrap: wrap;
  gap: 12px 24px; align-items: flex-end; justify-content: space-between; }
.top h1 { margin: 0; font-size: 20px; }
.top p { margin: 4px 0 0; color: var(--muted); max-width: 660px; }
.widths { display: flex; gap: 2px; background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 3px; }
.widths span { color: var(--muted); padding: 4px 6px 4px 8px; }
.widths button { border: 0; background: none; padding: 4px 10px; border-radius: 6px; cursor: pointer;
  color: var(--muted); font: inherit; }
.widths button[aria-pressed="true"] { background: var(--green); color: #fff; }
.cols { display: flex; flex-wrap: wrap; justify-content: center; gap: 36px; padding: 18px 16px 48px; }
.col { width: var(--phone); max-width: 100%; }
.col h2 { font-size: 16px; margin: 0 0 8px; }
.col h2 small { font-weight: 400; color: var(--muted); margin-left: 6px; }
.actions { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.actions button { font: inherit; font-size: 13px; padding: 5px 12px; border-radius: 999px; cursor: pointer;
  border: 1px solid var(--green); background: #fff; color: var(--green); }
.actions button.primary { background: var(--green); color: #fff; }
.check { margin: 0 0 12px; padding: 8px 12px; border-radius: 10px; background: #fff; border: 1px solid var(--line); font-size: 13px; }
.check.bad { border-color: #f5c27a; background: #fff8ec; }
.check summary { cursor: pointer; font-weight: 600; }
.check ul { margin: 6px 0 2px; padding-left: 18px; color: var(--warn); }
.check li.hint { color: var(--muted); }
.phone { background: #fff; border-radius: 22px; overflow: hidden;
  box-shadow: 0 0 0 1px var(--line), 0 12px 32px rgba(31, 42, 33, .12); }
.screen { height: min(800px, 82vh); overflow-y: auto; scrollbar-width: none; }
.screen::-webkit-scrollbar { display: none; }  /* 手机上滚动条不占宽度，预览里也不能占 */

/* 仿公众号文章页（rich_media_* 为公众号原样式要点） */
.rich_media_area_primary { padding: 20px 16px 12px; }
.rich_media_title { font-size: 22px; line-height: 1.4; font-weight: 700; margin: 0 0 14px; color: rgba(0, 0, 0, .9); }
.rich_media_meta { font-size: 15px; color: #576b95; margin-bottom: 22px; }
.rich_media_content { overflow: hidden; color: rgba(0, 0, 0, .9); font-size: 17px; line-height: 1.6;
  word-wrap: break-word; text-align: justify;
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "PingFang SC", "Hiragino Sans GB",
    "Microsoft YaHei UI", "Microsoft YaHei", Arial, sans-serif; }
.rich_media_content * { max-width: 100% !important; box-sizing: border-box !important; word-wrap: break-word !important; }
.rich_media_content p { margin: 0; clear: both; min-height: 1em; }
.mock-video { position: relative; aspect-ratio: 16 / 9; background: #20262a center / cover no-repeat; }
.mock-video::before { content: ""; position: absolute; left: 50%; top: 50%; width: 54px; height: 54px;
  margin: -27px 0 0 -27px; border-radius: 50%; border: 1.5px solid rgba(255, 255, 255, .85);
  background: rgba(255, 255, 255, .28) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M9 7v10l8-5z' fill='white'/%3E%3C/svg%3E") center / 30px no-repeat; }
.mock-video::after { content: attr(data-len); position: absolute; right: 10px; bottom: 6px; color: #fff;
  font-size: 13px; text-shadow: 0 1px 3px rgba(0, 0, 0, .6); }
.toast { position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%); background: rgba(31, 42, 33, .92);
  color: #fff; padding: 8px 16px; border-radius: 999px; opacity: 0; transition: opacity .2s; pointer-events: none; }
.toast.show { opacity: 1; }
</style>
</head>
<body>
<header class="top">
  <div>
    <h1>推文排版预览</h1>
    <p>「复制排版」→ 公众号后台新建图文，正文里粘贴 → 在黄色虚线框处插入视频并删掉虚线框 →「复制标题」填进标题栏 → 手机预览确认。</p>
  </div>
  <div class="widths" role="group" aria-label="预览手机宽度">
    <span>手机宽度</span><button data-w="360">360</button><button data-w="375">375</button><button data-w="390" aria-pressed="true">390</button><button data-w="430">430</button>
  </div>
</header>
<main class="cols" id="cols"></main>
<div class="toast" id="toast" role="status"></div>
<script>
const DATA = /*__DATA__*/null;
const WIDTHS = [360, 375, 390, 430];
let current = 390;

const toast = msg => {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => t.classList.remove('show'), 1800);
};

function copy(html, text) {
  const onCopy = e => {
    if (html) e.clipboardData.setData('text/html', html);
    e.clipboardData.setData('text/plain', text);
    e.preventDefault();
  };
  document.addEventListener('copy', onCopy);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
  document.removeEventListener('copy', onCopy);
  return ok;
}

const setPhone = w => document.documentElement.style.setProperty('--phone', w + 'px');

// 元素里的文字排成了几行：只看文字（不看装饰图片和块元素），上沿相差 3px 以内算同一行
function lineCount(el) {
  const tops = [];
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let n; (n = walker.nextNode());) {
    if (!n.data.trim()) continue;
    const r = document.createRange(); r.selectNodeContents(n);
    for (const x of r.getClientRects()) if (x.width > 0) tops.push(x.top);
  }
  tops.sort((m, n) => m - n);
  return tops.filter((t, i) => i === 0 || t - tops[i - 1] > 3).length;
}

// 两端对齐被撑开的行：该行汉字平均占宽比“字号 + 字距”多出 4px 以上
function stretchedLines(p) {
  const cs = getComputedStyle(p);
  const advance = parseFloat(cs.fontSize) + (parseFloat(cs.letterSpacing) || 0);
  const lines = new Map();
  const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
  for (let n; (n = walker.nextNode());) {
    for (let i = 0; i < n.data.length; i++) {
      const ch = n.data[i];
      if (ch.charCodeAt(0) <= 0x2e80) continue;
      const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 1);
      const rect = r.getClientRects()[0];
      if (!rect) continue;
      const k = Math.round(rect.top);
      if (!lines.has(k)) lines.set(k, []);
      lines.get(k).push([ch, rect.width]);
    }
  }
  const out = [];
  for (const chars of lines.values()) {
    const avg = chars.reduce((s, c) => s + c[1], 0) / chars.length;
    if (avg - advance > 4) out.push(chars.map(c => c[0]).join(''));
  }
  return out;
}

function selfCheck(content) {
  const errors = [], hints = [];
  for (const w of WIDTHS) {
    setPhone(w);
    const cr = content.getBoundingClientRect();
    if (content.scrollWidth > content.clientWidth + 1) errors.push(`${w}px：内容横向溢出`);
    content.querySelectorAll('[data-chk="q"] p').forEach(p => {
      if (lineCount(p) > 1) errors.push(`${w}px：问题折行「${p.textContent}」`);
    });
    content.querySelectorAll('[data-chk="title"]').forEach(t => {
      const r = t.getBoundingClientRect();
      if (lineCount(t) > 1 || r.left < cr.left - 0.5 || r.right > cr.right + 0.5)
        errors.push(`${w}px：分区标题放不下「${t.textContent}」`);
    });
    content.querySelectorAll('[data-chk="ans"] p').forEach(p => {
      for (const line of stretchedLines(p)) hints.push(`${w}px：字距被撑大「${line}」`);
    });
  }
  setPhone(current);
  return { errors, hints };
}

const cols = document.getElementById('cols');
for (const a of DATA) {
  const col = document.createElement('div');
  col.className = 'col';
  col.innerHTML = `
    <h2><span></span><small></small></h2>
    <div class="actions">
      <button class="primary" data-act="rich">复制排版</button>
      <button data-act="html">复制源码</button>
      <button data-act="title">复制标题</button>
    </div>
    <details class="check"><summary></summary><ul></ul></details>
    <div class="phone"><div class="screen"><div class="rich_media_area_primary">
      <h1 class="rich_media_title"></h1>
      <div class="rich_media_meta"></div>
      <div class="rich_media_content">${a.preview}</div>
    </div></div></div>`;
  col.querySelector('h2 span').textContent = a.name;
  col.querySelector('h2 small').textContent = '模板：' + a.template;
  col.querySelector('.rich_media_title').textContent = a.title;
  col.querySelector('.rich_media_meta').textContent = a.account;
  col.querySelector('.actions').addEventListener('click', e => {
    const act = e.target.dataset.act;
    if (!act) return;
    const ok = act === 'rich' ? copy(a.html, a.text) : act === 'html' ? copy(null, a.html) : copy(null, a.title);
    toast(ok ? { rich: '已复制排版，去公众号正文粘贴', html: '已复制 HTML 源码', title: '已复制标题' }[act]
             : '复制失败，请改用对应的 .html 文件');
  });
  cols.appendChild(col);
  col.lint = a.lint;
}

// 图片加载完再自检（头图高度会影响布局）
window.addEventListener('load', () => {
  for (const col of cols.children) {
    const { errors, hints } = selfCheck(col.querySelector('.rich_media_content'));
    const all = [...col.lint.map(x => '规范：' + x), ...errors];
    const box = col.querySelector('.check');
    box.classList.toggle('bad', all.length > 0);
    box.querySelector('summary').textContent = all.length
      ? `⚠️ 自检发现 ${all.length} 处问题` : `✅ 自检通过（360 / 375 / 390 / 430）${hints.length ? `，${hints.length} 处可选优化` : ''}`;
    box.querySelector('ul').innerHTML = '';
    for (const [list, cls] of [[all, ''], [hints, 'hint']]) for (const t of list) {
      const li = document.createElement('li'); li.className = cls; li.textContent = t;
      box.querySelector('ul').appendChild(li);
    }
    if (all.length) box.open = true;
  }
});

document.querySelector('.widths').addEventListener('click', e => {
  const w = +e.target.dataset.w;
  if (!w) return;
  current = w; setPhone(w);
  for (const b of e.currentTarget.querySelectorAll('button')) b.setAttribute('aria-pressed', b === e.target);
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
