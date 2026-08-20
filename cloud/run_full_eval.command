#!/bin/zsh
set -euo pipefail

cd "${0:A:h}"
service='Ecclesia QA Access'
account="$(id -un)"
if ! task_access_key=$(security find-generic-password -a "$account" -s "$service" -w 2>/dev/null); then
  echo 'Enter the Ecclesia access key at the hidden prompt. It will be stored in macOS Keychain, not the repository or shell history.'
  read -rs "task_access_key?Ecclesia access key: "
  echo
  security add-generic-password -U -a "$account" -s "$service" -w "$task_access_key"
fi

mkdir -p ../output/eval
preview_url="${ECCLESIA_PREVIEW_URL:-https://phase4e-release-ecclesia-qa.ecclesia-qa-2026.workers.dev}"
npm run eval:central-theme
npm test
baseline_status=0
preview_status=0
ACCESS_KEY="$task_access_key" npm run eval | tee ../output/eval/phase2b-baseline.json || baseline_status=$?
ACCESS_KEY="$task_access_key" ECCLESIA_BASE_URL="$preview_url" npm run eval | tee ../output/eval/phase2b-preview.json || preview_status=$?
unset task_access_key
if (( baseline_status != 0 || preview_status != 0 )); then
  echo "Evaluation failed: production=$baseline_status preview=$preview_status" >&2
  exit 1
fi
echo 'Baseline and preview evaluations complete. You may close this window.'
if [[ -t 0 ]]; then
  read -r '?Press Return to close.'
fi
