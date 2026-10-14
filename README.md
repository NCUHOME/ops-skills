# 教务答疑直通车 · 公众号推文排版 skill

把一份问答文档（docx / 文字，可以配视频），交给 Claude Code，排成和南昌大学教务处「教务答疑直通车」推文一样的版式：头图、视频提示条、绿色分区标题、编号问答卡片、温馨提示。排好的内容能直接粘贴进公众号编辑器。

![预览页：两篇推文的手机预览、一键复制和排版自检](docs/preview.png)

版式从已发布的「教务答疑直通车｜第三期：南昌大学本科新生秋季学期选课 Q&A」逐项复刻，样式数值和图片都是原推文里的。

> 你不需要会写代码。你要做的是：**准备好文档和视频 → 用下面的提示词告诉 Claude → 在预览页检查 → 复制、粘贴进公众号**。

---

## 一、安装（只需一次）

需要先装好：

- [Claude Code](https://claude.com/claude-code)
- [Node.js](https://nodejs.org)（安装 skill 时用）
- Python 3.8 以上（生成排版时用）

下面两个是可选的：

- pandoc：读取 Word 文档。macOS 上用 `brew install pandoc` 安装。
- ffmpeg：自动读取视频时长、截取封面帧。macOS 上用 `brew install ffmpeg` 安装。

```bash
# 装到当前项目（在你放材料的文件夹里运行）
npx skills add NCUHOME/wechat-qa-layout -a claude-code

# 或者装给自己，所有项目都能用
npx skills add NCUHOME/wechat-qa-layout -a claude-code -g
```

不用 npx 也可以：把仓库里的 `skills/wechat-qa-layout` 文件夹复制到 `~/.claude/skills/`（所有项目可用），或者复制到项目的 `.claude/skills/`。

---

## 二、准备这些材料

| 材料 | 必需？ | 说明 |
|---|---|---|
| **文案** | 必需 | 问答文档（.docx / .pdf / 文字），并说明本篇用其中哪一部分。问题和答案会逐字照抄 |
| **视频** | 有就给 | 视频文件路径。有多段视频时，Claude 会看片头认出哪段对应哪篇 |
| **标题** | 建议 | 公众号标题栏用的完整标题，例如「教务答疑直通车｜第八期：南昌大学本科生选课 Q&A（选课篇）」。片头上写了标题的话可以不给 |
| **口径** | 有就给 | 文档里说法不一致的地方以哪个为准 |

---

## 三、提示词模板（直接复制，改掉【】里的内容）

### 1. 排一篇或几篇推文

```text
用 wechat-qa-layout 排推文：
- 文案：【/Users/xxx/Downloads/常见问题指南.docx】，用其中【「缓免测」】这一部分
- 视频：【/Users/xxx/Downloads/缓免测篇.mp4】
- 标题：【教务答疑直通车｜第六期：南昌大学《学生体质健康标准》Q&A（缓免测篇）】
```

两段视频对应同一份文档的两部分时，把两个视频都给它，并说“两篇都排”。

### 2. 看完预览后提修改意见

```text
几处修改：
1. 第二个分区的标题改成「……」
2. 「免测申请是否跨学年持续生效？」这一问的答案不要加粗
3. 结尾的祝福语删掉
改完重新生成
```

### 3. 两行放不下的问题

问题标题最多两行。原问题太长时，Claude 会列出来让你精简，例如：

```text
第 4 问改成：疾病证明限南昌医院吗？ / 须为本学期诊断材料吗？
```

---

## 四、生成之后

每篇得到一个 `.html`（正文代码），所有篇共用一个 `预览.html`。

1. 用浏览器打开 `预览.html`。每篇上方有**自检**结果：页面会在 360、375、390、430 四种手机宽度下，检查问题有没有折行、标题有没有撑出、字距有没有被撑大。
2. 点「**复制排版**」，到公众号后台新建图文，在正文里粘贴。
3. 在**黄色虚线框**处插入视频，然后删掉虚线框。
4. 点「**复制标题**」，填进标题栏。
5. 用手机预览确认，再交给负责发布的人。

## 五、不用 Claude，自己生成

按 [`skills/wechat-qa-layout/references/FORMAT.md`](skills/wechat-qa-layout/references/FORMAT.md) 的格式写一个 `.md` 文件，然后运行：

```bash
python3 skills/wechat-qa-layout/scripts/build.py 我的推文.md -o 输出文件夹
python3 skills/wechat-qa-layout/scripts/build.py --check 我的推文.md   # 只检查规范，不生成
```

可以拿这两个示例来改：

- [`examples/缓免测篇.md`](skills/wechat-qa-layout/examples/缓免测篇.md)：一篇完整的推文；
- [`examples/格式示例.md`](skills/wechat-qa-layout/examples/格式示例.md)：演示没有视频、网址、列表、段内换行等写法。

---

## 六、排版规范

这些规范来自真实的审稿意见，生成时会自动检查：

- **问题标题最多两行，每行不超过 12 字。** 三行、四行很难看；每行超过 12 字，在 360px 宽的安卓手机上会折行。原问题太长时，由审稿人精简，不要硬拆成三四行。
- 分区标题不超过 15 字。
- 问题和答案逐字照抄原文。只允许做这些排版处理：去掉数字与汉字之间的空格、长答案分段、补句末标点、加粗重点。
- 视频要在公众号编辑器里插入，代码里只留一个占位框。

## 七、换单位、栏目或版式

- **换颜色、logo、栏目名**：复制 `templates/jwdy.json` 改一份，生成时加上 `--template 新文件.json`。图片必须先上传到公众号，再使用它的图片地址（`mmbiz.qpic.cn` 开头）。
- **照另一篇推文复刻全新版式**：见 [`references/NEW-LAYOUT.md`](skills/wechat-qa-layout/references/NEW-LAYOUT.md)。

---

## 附：文件结构

```
skills/wechat-qa-layout/
  SKILL.md              Claude 的做法：流程、硬性要求、交付清单
  scripts/build.py      文案 .md → 粘贴用 HTML + 预览页（只用 Python 标准库）
  scripts/outline.py    拆解参考推文代码的结构
  templates/jwdy.json   「教务答疑直通车」版式：颜色、头图叠层、图片地址、字数限制
  references/           文案写法（FORMAT.md）、复刻新版式（NEW-LAYOUT.md）
  examples/             示例文案
```

同系列：[explainer-kit](https://github.com/NCUHOME/explainer-kit)，把政策文档做成动画说明视频。第三方资源说明见 [NOTICE.md](NOTICE.md)。
