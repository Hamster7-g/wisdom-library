#!/usr/bin/env bash
# 智慧库 → GitHub 一键推送
#
# 用法：
#   bash tools/push_to_github.sh <github用户名> <仓库名>
#   bash tools/push_to_github.sh Scamander wisdom-library
#
# 前置条件（二选一）：
#   A) 已把本机 SSH 公钥添加到 GitHub 账号
#      公钥内容：cat ~/.ssh/id_ed25519.pub
#      添加位置：GitHub → Settings → SSH and GPG keys → New SSH key
#   B) 已配置 https 凭据（Personal Access Token），首次 push 时按提示输入

set -euo pipefail

USER_NAME="${1:-}"
REPO_NAME="${2:-wisdom-library}"

if [[ -z "$USER_NAME" ]]; then
  echo "用法: bash tools/push_to_github.sh <github用户名> [仓库名]"
  echo
  echo "查看本机公钥（需添加到 GitHub 账号）:"
  echo "  cat ~/.ssh/id_ed25519.pub"
  exit 1
fi

REPO_NAME="${REPO_NAME:-wisdom-library}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SSH_URL="git@github.com:${USER_NAME}/${REPO_NAME}.git"

echo "仓库根目录: $ROOT"
echo "目标远程  : $SSH_URL"
echo

# 1. 设置远程
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$SSH_URL"
  echo "[1/4] 已更新 origin -> $SSH_URL"
else
  git remote add origin "$SSH_URL"
  echo "[1/4] 已添加 origin -> $SSH_URL"
fi

# 2. 确保在 main 分支
git branch -M main 2>/dev/null || true
echo "[2/4] 当前分支: $(git rev-parse --abbrev-ref HEAD)"

# 3. 提交本地改动
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "同步本地更新"
  echo "[3/4] 已提交本地改动"
else
  echo "[3/4] 无本地改动，跳过提交"
fi

# 4. 推送
echo "[4/4] 推送中..."
if git push -u origin main; then
  echo
  echo "推送成功 → https://github.com/${USER_NAME}/${REPO_NAME}"
else
  echo
  echo "推送失败。常见原因与对策："
  echo "  · 'Permission denied (publickey)' → 公钥未添加，输出 cat ~/.ssh/id_ed25519.pub 贴到 GitHub"
  echo "  · 'Repository not found'          → 远程仓库不存在，先在 GitHub 网页建一个空仓库（不要勾选 README）"
  echo "  · 'Could not resolve host'        → 网络需要代理，先设好 git 代理"
  exit 1
fi
