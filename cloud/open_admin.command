#!/bin/zsh
set -euo pipefail

task_admin_key=$(security find-generic-password -a "$(id -un)" -s "Ecclesia QA Admin" -w)
printf '%s' "$task_admin_key" | pbcopy
open "https://ecclesia-qa.ecclesia-qa-2026.workers.dev/admin"
echo "Ecclesia QA 管理员密钥已复制到剪贴板；请粘贴到刚打开的后台页面。"
