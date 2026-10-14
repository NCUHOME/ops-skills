#!/bin/bash
# 找到或准备视频引擎（NCUHOME/explainer-kit）的工作区，最后一行输出工作区路径。
#
# 用法：bash workspace.sh [工作区路径]
# 查找顺序：参数 → 当前文件夹 → 当前文件夹下的 explainer-kit/ → 环境变量 EXPLAINER_KIT → ~/explainer-kit
# 都没有：下载到参数给的位置（默认 ~/explainer-kit），并运行 setup.sh（第一次约 2 分钟）。
set -e

is_kit() { [ -n "$1" ] && [ -f "$1/tools/new_episode.py" ] && [ -d "$1/video" ]; }

kit=""
for c in "${1:-}" "$PWD" "$PWD/explainer-kit" "${EXPLAINER_KIT:-}" "$HOME/explainer-kit"; do
  if is_kit "$c"; then kit="$c"; break; fi
done

if [ -z "$kit" ]; then
  kit="${1:-$HOME/explainer-kit}"
  echo "· 下载视频引擎到 $kit" >&2
  git clone -q https://github.com/NCUHOME/explainer-kit.git "$kit" >&2
fi
cd "$kit"

# 有更新就拉取；本地有改动（比如正在做的期）时不动，免得冲掉
if [ -d .git ]; then
  if [ -z "$(git status --porcelain)" ]; then
    git pull -q --ff-only >&2 || echo "· 拉取更新失败，先用本地版本" >&2
  else
    echo "· 工作区有未提交的改动，这次不自动更新" >&2
  fi
fi

if [ ! -d video/node_modules ] || [ ! -x .venv/bin/python ]; then
  echo "· 第一次使用，运行 setup.sh（约 2 分钟）" >&2
  ./setup.sh >&2
fi

if [ ! -d brands ]; then
  echo "· 这个工作区还是旧版本（没有品牌库），请先在工作区运行 git pull" >&2
elif [ ! -f video/public/brand/brand.json ]; then
  python3 tools/brand.py use ncu-jwc >&2
fi

pwd
