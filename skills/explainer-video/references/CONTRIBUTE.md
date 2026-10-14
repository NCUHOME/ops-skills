# 把新品牌存进品牌库（提 PR）

品牌库在视频引擎仓库 https://github.com/NCUHOME/explainer-kit 的 `brands/` 里，收任何单位的品牌。所有改动都要提 PR，由维护人审核后合并。**绝不直接推到 main。**

只有用户同意存进品牌库，才按下面的步骤做。

## 1. 补齐品牌文件夹

工作区里的 `brands/<品牌名>/` 要有：

- `brand.json`，全部字段都要填（字段说明在 `tools/brand.py` 开头）：
  - `order`：取品牌库当前最大编号 + 1；
  - `name`：品牌名称，例如「南昌大学学生工作处 · 学工小课堂」；
  - `description`：一句话说明；
  - `rights`：标志归谁所有、能不能放进公开仓库。拿不准就问用户，不要自己判断。
- 组合标志图片（如果有）。

运行 `python3 tools/brand.py check`，必须全部 ✓。

## 2. 只提交品牌文件夹

工作区里通常还有用户自己做的期（`video/src/episodes/<期>/`、`index.ts`）。这些可能有没公开的内容，**不要提交**。

```bash
git switch -c brand/<品牌名>               # 未提交的改动会留在工作区，不受影响
git add brands/<品牌名>                     # 只加品牌文件夹
git add docs/LESSONS.md                    # 用户同意一起提交审片意见时才加
git status                                 # 确认暂存区只有上面这些
```

先把暂存的改动清单给用户看。用户确认后再提交：

```bash
git commit -m "新品牌：<名称>"
```

## 3. 推送并提 PR

**有仓库写权限**（`gh api repos/NCUHOME/explainer-kit --jq .permissions.push` 输出 `true`）：

```bash
git push -u origin brand/<品牌名>
gh pr create --repo NCUHOME/explainer-kit --base main --title "新品牌：<名称>" --body-file <填好的说明>
```

**没有写权限**：

```bash
gh repo fork --remote                     # 原仓库变成 upstream，自己的 fork 变成 origin
git push -u origin brand/<品牌名>
gh pr create --repo NCUHOME/explainer-kit --base main --head <自己的GitHub用户名>:brand/<品牌名> \
  --title "新品牌：<名称>" --body-file <填好的说明>
```

**用户没有 GitHub 账号，或者没装 gh**：把 `brands/<品牌名>/` 打包发给维护人，请维护人代为提交。

PR 说明按仓库里的 `.github/pull_request_template.md` 填。提交后 GitHub 会自动跑品牌库检查，结果显示在 PR 页面上。

提完 PR，用 `git switch -` 回到原来的分支，用户的期照常在工作区里。

## 4. 合并之后

告诉用户：

- PR 链接；
- 维护人合并后，`workspace.sh` 会在工作区没有未提交改动时自动拉取更新，新品牌就会出现在品牌一览里。工作区有改动时，在工作区手动运行 `git pull`；
- 在合并之前，这个品牌在本机照样可以用。
