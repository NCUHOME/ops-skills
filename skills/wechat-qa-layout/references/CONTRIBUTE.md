# 把新模板存进模板库（提 PR）

模板库在 https://github.com/NCUHOME/wechat-qa-layout ，收任何单位的版式。所有改动都要提 PR，由维护人审核后合并。**绝不直接推到 main。**

只有用户同意存进模板库，才按下面的步骤做。

## 1. 补齐模板文件夹

`./推文模板/<模板名>/` 里要有这些文件：

| 文件 | 怎么来 |
|---|---|
| `template.json` | 做模板时写好的。`order` 取模板库里当前最大编号 + 1；`source`、`rights` 必须填 |
| `components.py` | 只有结构和默认模板不同时才有 |
| `example.md` | 示例文案，信息区不写「模板」。可以用这次的文章，但还没公开发布、或者口径没定的内容，要先换成示意内容 |
| `preview.png` | 进了仓库再生成：`python3 scripts/thumbnail.py <模板名>` |
| `snapshot.html` | 进了仓库再生成：`python3 scripts/check_templates.py --update <模板名>` |

`rights` 写清楚图片和 logo 归谁所有、能不能放进公开仓库。拿不准就问用户，不要自己判断。

## 2. 在仓库副本里加模板

```bash
gh repo clone NCUHOME/wechat-qa-layout ~/wechat-qa-layout   # 已经有了就 cd 进去 git switch main && git pull
cd ~/wechat-qa-layout
git switch -c template/<模板名>
cp -R <工作文件夹>/推文模板/<模板名> skills/wechat-qa-layout/templates/<模板名>
cd skills/wechat-qa-layout
python3 scripts/thumbnail.py <模板名>
python3 scripts/check_templates.py --update <模板名>
python3 scripts/check_templates.py        # 必须全部 ✓：旧模板的快照一个字节都不能变
```

然后在仓库根目录 `README.md` 的「模板库」表格里加一行。

如果为了这个模板改了 `scripts/` 里的公共代码，旧模板的快照必须仍然不变。真要改旧模板的样子，必须在 PR 里单独说明，等维护人同意。

## 3. 给用户看改动，确认后提 PR

先把改动清单给用户看：`git status`、`git diff --stat`，并说明新增了什么、有没有改公共代码。用户确认后：

```bash
git add -A
git commit -m "新模板：<名称>（<公众号>）"
```

**有仓库写权限**（`gh api repos/NCUHOME/wechat-qa-layout --jq .permissions.push` 输出 `true`）：

```bash
git push -u origin template/<模板名>
gh pr create --repo NCUHOME/wechat-qa-layout --base main --title "新模板：<名称>" --body-file <填好的说明>
```

**没有写权限**：

```bash
gh repo fork --remote                     # 原仓库变成 upstream，自己的 fork 变成 origin
git push -u origin template/<模板名>
gh pr create --repo NCUHOME/wechat-qa-layout --base main --head <自己的GitHub用户名>:template/<模板名> \
  --title "新模板：<名称>" --body-file <填好的说明>
```

**用户没有 GitHub 账号，或者没装 gh**：把 `推文模板/<模板名>/` 打包发给维护人，请维护人代为提交。

PR 说明照仓库里的 `.github/pull_request_template.md` 填，把缩略图也贴上去。提交后 GitHub 会自动跑一遍模板检查，结果显示在 PR 页面上；没通过就按报错修好再推。

## 4. 合并之后

告诉用户：

- PR 链接；
- 维护人合并后，大家在装 skill 的文件夹里运行 `npx skills update`，新模板就会出现在模板一览里；
- 在合并之前，这个模板照样可以用：文案里写 `模板: 推文模板/<模板名>` 就行。
