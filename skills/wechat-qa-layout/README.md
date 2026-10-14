# 推文排版 skill（wechat-qa-layout，带模板库）

把一份问答文档（docx / 文字，可以配视频）交给 Claude Code，按选定的模板排成公众号推文，排好的内容能直接粘贴进公众号编辑器。模板库里有南昌大学教务处「教务答疑直通车」等版式。给一篇已发布推文的链接，就能复刻它的版式；做好的新版式可以提交到模板库，所有人都能用。

![预览页：两篇推文的手机预览、一键复制和排版自检](../../docs/preview.png)

> 你不需要会写代码。你要做的是：**选模板 → 发材料 → 在预览页检查 → 复制、粘贴进公众号**。

---

## 一、安装（只需一次）

需要先装好：

- [Claude Code](https://claude.com/claude-code)
- [Node.js](https://nodejs.org)（安装 skill 时用）
- Python 3.8 以上（生成排版时用）

下面几个是可选的：

- pandoc：读取 Word 文档。macOS 上用 `brew install pandoc` 安装。
- ffmpeg：自动读取视频时长、截取封面帧。macOS 上用 `brew install ffmpeg` 安装。
- Chrome 或 Edge：生成模板缩略图，做新模板时才用到。

```bash
# 装运营组全部 skill（推文排版 + 做视频），装给自己，所有项目都能用
npx skills add NCUHOME/ops-skills -a claude-code -g

# 只装推文排版
npx skills add NCUHOME/ops-skills -a claude-code -g -s wechat-qa-layout

# 以后模板库有更新，运行这一句
npx skills update
```

---

## 二、使用流程

| 步骤 | 你做什么 | Claude 做什么 |
|---|---|---|
| 1. 开始 | 输入 `/wechat-qa-layout`，或直接说「帮我排推文」 | 打开「模板一览」网页，出一道选择题：选已有模板，或者「照一篇新推文做」 |
| 2. 选模板 | 点选项，或回复编号 | 列出这次需要的材料 |
| 3. 发材料 | 在**同一个对话**里发文案、视频、标题和要求 | 照抄问答、分区、断行、加粗，生成预览网页，四种手机宽度自检 |
| 4. 审稿 | 在预览页看效果，提修改意见 | 修改，重新生成 |
| 5. 发布 | 「复制排版」→ 粘贴进公众号正文 → 在黄色虚线框处插入视频 →「复制标题」→ 手机预览 → 交给发布人 | —— |
| 6. 存模板 | 只有这次做了新版式才会被问：要不要存进模板库 | 同意的话，补齐模板文件、跑回归检查，你确认改动后提 PR |

### 第 3 步要发的材料

| 材料 | 说明 |
|---|---|
| **文案** | 问答文档，并说明用其中哪一部分。问题和答案会逐字照抄 |
| **视频** | 有就给文件路径，可以有多段。Claude 会看片头认出哪段对应哪篇 |
| **标题** | 公众号标题栏用的完整标题。片头上写了就可以不给 |
| **口径** | 文档里说法不一致的地方，以哪个为准 |
| **参考推文链接** | 只有「照一篇新推文做」时才需要：一篇已发布推文的链接，再告诉 Claude 新模板叫什么名字 |

示例：

```text
文案：/Users/xxx/Downloads/常见问题指南.docx，用其中「缓免测」这一部分
视频：/Users/xxx/Downloads/缓免测篇.mp4
标题：教务答疑直通车｜第六期：南昌大学《学生体质健康标准》Q&A（缓免测篇）
```

---

## 三、模板库

| 编号 | 模板 | 公众号 | 特点 |
|---|---|---|---|
| 1 | 教务答疑直通车（`jwdy`） | 南昌大学教务处 | 清新绿配暖黄：枝叶头图、绿色分区条、黄色圆形编号和虚线问题框，适合政策问答 |

每个模板是 `templates/` 下的一个文件夹：

| 文件 | 内容 |
|---|---|
| `template.json` | 颜色、图片、头图叠层、字数限制、来源和版权说明 |
| `components.py` | 只有结构不同的模板才有 |
| `example.md` | 示例文案 |
| `preview.png` | 缩略图 |
| `snapshot.html` | 回归快照 |

### 贡献模板

做了新版式，Claude 会问要不要存进模板库，同意后它会自动帮你提 PR。手动提交的步骤见 [`references/CONTRIBUTE.md`](references/CONTRIBUTE.md)：

1. 所有模板都通过 PR 合并，由维护人审核。PR 会自动跑模板检查。
2. 提交前必须跑 `check_templates.py`，旧模板的生成结果一个字节都不能变。
3. 图片要用公众号图床链接，并写清版权归属。

---

## 四、排版规范

这些规范来自真实的审稿意见，生成时会自动检查：

- **问题标题最多两行，每行不超过 12 字。** 三行、四行很难看；每行超过 12 字，在 360px 宽的安卓手机上会折行。原问题太长时，由审稿人精简，不要硬拆成三四行。
- 分区标题不超过 15 字。
- 问题和答案逐字照抄原文。只允许做这些排版处理：去掉数字与汉字之间的空格、长答案分段、补句末标点、加粗重点。
- 视频要在公众号编辑器里插入，代码里只留一个占位框。

## 五、不用 Claude，自己生成

按 [`references/FORMAT.md`](references/FORMAT.md) 的格式写一个 `.md` 文件（可以复制 [`templates/jwdy/example.md`](templates/jwdy/example.md) 来改），然后在本文件夹运行：

```bash
python3 scripts/gallery.py -o 模板一览.html              # 看有哪些模板
python3 scripts/build.py 我的推文.md -o 输出文件夹         # 生成；信息区写「模板: 模板名」选模板
python3 scripts/build.py --check 我的推文.md              # 只检查规范，不生成
```

---

## 附：文件结构

```
wechat-qa-layout/
  SKILL.md                    Claude 的做法：选模板 → 列材料 → 生成 → 审稿 → 存模板
  scripts/build.py            文案 .md → 粘贴用 HTML + 预览页（只用 Python 标准库）
  scripts/gallery.py          模板一览网页
  scripts/fetch_article.py    从公众号文章链接取正文代码
  scripts/outline.py          拆解参考推文代码的结构
  scripts/thumbnail.py        生成模板缩略图
  scripts/check_templates.py  模板库检查和回归快照
  templates/<模板名>/          模板库
  references/                 文案写法、做新模板、提交模板
  examples/                   格式示例
```

同一合集里还有 [做视频 skill](../explainer-video/)。第三方资源说明见 [NOTICE.md](../../NOTICE.md)。
