# 照一篇参考推文做新模板

默认模板 `jwdy` 就是按下面的步骤，从「教务答疑直通车」第三期复刻出来的。新模板先放在用户工作文件夹的 `./推文模板/<模板名>/`，用户认可、决定存进模板库时，再按 `CONTRIBUTE.md` 提 PR。

模板名只用小写字母、数字和连字符，例如 `ncuhome-blue`。

## 1. 取参考推文的代码

```bash
python3 scripts/fetch_article.py "https://mp.weixin.qq.com/s/xxxx" -o 参考.html
```

- 脚本会打印文章标题和公众号名，写进 `template.json` 的 `source`。
- 取不到时（触发验证页、文章是草稿），让用户这样拿：用电脑浏览器打开文章，打开开发者工具，选中正文节点 `#js_content`，右键 Copy → Copy outerHTML，存成 `参考.html`。

## 2. 拆结构

```bash
python3 scripts/outline.py 参考.html            # 缩进大纲：标签、关键样式、文字、图片编号
python3 scripts/outline.py 参考.html --images   # 全部图片链接，按出现顺序去重
```

认出构件：头图、视频提示条、分区标题、卡片、问题行、答案段、结尾。同一种构件出现多次时，对比几处的样式，分清哪些是固定的、哪些会变（文字、编号、上边距）。

## 3. 建模板文件夹

把 `templates/jwdy/` 整个复制到 `./推文模板/<模板名>/`，然后按参考推文改。分两种情况：

**只换皮**（结构和 jwdy 一样，只是颜色、图片、头图不同）：只改 `template.json`。

| 字段 | 内容 |
|---|---|
| `order` `name` `account` `description` | 编号（排在最后）、模板名称、公众号名、一句话特点 |
| `source` | 参考推文的 `title`、`account`、`url` |
| `rights` | 图片和 logo 的版权归属，以及能不能放进公开的模板库（不确定就问用户） |
| `colors` | 主色、点缀色、底色等，取自参考推文的行内样式 |
| `images` | 用到的图片链接（必须是 `mmbiz.qpic.cn` 公众号图床），起个短名字 |
| `header` | 头图叠层：每层是 `[宽%, 高%, 左边距%, 上边距%, 字号px, 图片名]`，标题框、副标题框的位置 |
| `section_deco` | 分区标题两侧装饰图 |
| `limits` | 字数限制，见第 5 步 |

**结构不同**（卡片、问题行、标题样式都不一样）：除了改 `template.json`，再写 `components.py`，用同名函数覆盖 `build.py` 里 `DEFAULT` 中的构件。没覆盖的构件沿用默认实现。

```python
# 推文模板/<模板名>/components.py
# 不用 import：E、P、rich、img、br、chk、BB、T（本模板的 template.json）、DEFAULT（默认构件）都能直接用

def section_title(text, pv):
    return E("section", f"margin: 40px 5% 12px; {BB}",
             E("section", f"border-bottom: 3px solid {T['colors']['main']}; padding: 0px 0px 4px; {BB}",
               P(f"margin: 0px; padding: 0px; color: {T['colors']['main']}; font-size: 17px; {BB}", f"**{text}**"),
               attrs=chk(pv, "title")))
```

可以覆盖的构件有：

| 构件 | 作用 |
|---|---|
| `header(a)` | 头图 |
| `video_blocks(a, pv)` | 视频提示条和视频位置 |
| `video_slot(...)` | 视频占位框和预览播放器，一般不用改 |
| `section_title(text, pv)` | 分区标题 |
| `question(n, lines, first, pv)` | 问题行：编号和问题框 |
| `paragraphs(paras, indent, pv)` | 答案或普通段落 |
| `card(sec, pv)` | 一个分区的卡片 |
| `tip(lines)` | 结尾温馨提示 |
| `article_html(a, pv)` | 整篇结构 |

写构件函数时要守住这几条：

- 用 `E("标签", "行内样式", 子元素…)` 拼结构，文字用 `P(样式, 文案)`，它会处理 `**加粗**`、反引号和 `\n`。
- 预览页自检靠三个标记定位，要原样保留：
  - 问题框加 `attrs=chk(pv, "q")`，每行问题是框里的一个 `<p>`；
  - 分区标题外框加 `chk(pv, "title")`；
  - 答案段落外框加 `chk(pv, "ans")`。
- 只能用行内样式。公众号会过滤 `<style>`、class、`position`、脚本和外链图片。

## 4. 抄样式时的坑

- **图片宽度**：导出的代码是渲染后的结果，图片宽度被写死成像素（例如 `width: 308px !important`）。真正的样式在 `data-original-style` 里，`outline.py` 已经替你取了这一项。
- **编辑器痕迹**：去掉 `visibility: visible`、`leaf=""`、`nodeleaf`、`data-*` 等属性。
- **视频**：视频是一大段 `<span class="video_iframe">` 播放器代码，`outline.py` 会把它折叠成一行，生成时换成占位框。
- **头图**：常见做法是用 `display: grid` 叠层。每层都写 `grid-row-start: 1; grid-column-start: 1`，用 `margin` 的百分比定位（`margin-top` 的百分比是相对**宽度**算的），文字放在 SVG 的 `foreignObject` 里。保留原结构，只换文字。
- **自己的新图片**：先在公众号后台上传到素材库或正文里，再复制它的图片地址。

## 5. 算字数限制

手机正文宽度 = 屏幕宽度 − 32px，360px 宽的手机是 328px。按新模板的卡片宽度、内边距、字号和字距算：

> 一行能放的字数 = 可用宽度 ÷（字号 + 字距）

把结果写进 `limits`：`question_line_chars`（问题每行字数）、`section_title_chars`（分区标题字数）。`question_lines` 固定为 2，问题标题最多两行。

## 6. 用新模板排这次的文案

在文案信息区写 `模板: 推文模板/<模板名>`，运行 `build.py`。打开 `预览.html`，和参考推文逐屏对比截图，看四种宽度下的自检结果。用户认可了才算做完。
