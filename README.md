# NCUHOME 运营组 Skills

运营组常用的 Claude Code skill 合集。装好以后，在 Claude Code 里用一句话就能开工：

| skill | 做什么 | 怎么开始 | 库 |
|---|---|---|---|
| [推文排版 `wechat-qa-layout`](skills/wechat-qa-layout/) | 把问答文档（可配视频）排成公众号推文，生成可以直接粘贴进公众号编辑器的代码、手机预览页和封面 | 输入 `/wechat-qa-layout`，或说「帮我排推文」 | **模板库**：选已有版式，或给一篇推文链接复刻新版式 |
| [做视频 `explainer-video`](skills/explainer-video/) | 把通知、办事指南或常见问题文档，做成带单位品牌、AI 配音、字幕和原创配乐的动画说明视频 | 输入 `/explainer-video`，或说「做视频」 | **品牌库**：选已有单位品牌，或新建一个 |

<table><tr>
<td><img src="docs/preview.png" alt="推文排版：手机预览、一键复制和排版自检" width="100%"></td>
<td><img src="docs/video.jpg" alt="做视频：教务答疑直通车 缓免测篇封面" width="100%"></td>
</tr></table>

---

## 安装

需要先装好：

- [Claude Code](https://claude.com/claude-code)
- [Node.js](https://nodejs.org) 20 以上
- Python 3.10 以上
- 做视频还需要 ffmpeg：macOS 上用 `brew install ffmpeg` 安装

```bash
# 两个 skill 一起装给自己，所有项目都能用
npx skills add NCUHOME/ops-skills -a claude-code -g

# 只装其中一个
npx skills add NCUHOME/ops-skills -a claude-code -g -s wechat-qa-layout
npx skills add NCUHOME/ops-skills -a claude-code -g -s explainer-video

# 以后有更新（新模板、新品牌、改进）
npx skills update
```

去掉 `-g` 就是只装到当前文件夹的项目里。第一次做视频时，Claude 会自动把视频引擎 [explainer-kit](https://github.com/NCUHOME/explainer-kit) 下载到 `~/explainer-kit` 并装好依赖，大约 2 分钟。

## 使用流程（两个 skill 一样）

1. **开始**：输入 `/skill名`，或者直接用一句话说要做什么。
2. **选择**：Claude 打开模板一览（推文）或品牌一览（视频）网页，出一道选择题。
3. **列材料**：Claude 说清这次需要哪些材料。
4. **发材料**：你在**同一个对话**里把文件和要求发过去。
5. **审稿**：推文在预览网页里看，视频看成片和截帧拼图；提意见，直到满意。
6. **入库**：这次做了新版式或新品牌，Claude 会问要不要存进库。同意后它会提 PR，由维护人审核合并，之后大家都能选。

两个 skill 共同遵守的原则：

- 内容逐字来自原文，任何改写都要列出来请你核对；
- 文档里的矛盾说法交给你定，Claude 不自己选；
- 交付前先自查。

## 贡献

- 新的推文模板：提交到本仓库的 `skills/wechat-qa-layout/templates/`。
- 新的视频品牌：提交到 [explainer-kit](https://github.com/NCUHOME/explainer-kit) 的 `brands/`。

两种都通过 PR 合并，由维护人审核。PR 会自动跑检查：推文模板检查旧模板的生成结果没变，视频品牌检查品牌库。平时直接对 Claude 说「存进模板库」或「存进品牌库」就行，具体步骤它都知道。

第三方资源说明见 [NOTICE.md](NOTICE.md)。
