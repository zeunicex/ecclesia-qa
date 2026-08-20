#!/bin/zsh
set -euo pipefail

cd "${0:A:h}/.."
package='phase4-batch-b'
state='pinecone-phase4-b-progress.json'
stats='pinecone-phase4-b-stats.json'
label='Batch B'
if [[ "${1:-}" == '--remaining' ]]; then
  package='phase4-remaining'
  state='pinecone-phase4-remaining-progress.json'
  stats='pinecone-phase4-remaining-stats.json'
  label='remaining priority prefix'
  shift
fi
if [[ "${1:-}" == '--clipboard' ]]; then
  pinecone_key="$(pbpaste)"
else
  echo 'Enter the rotated Pinecone API key. It will be used only by this process and will not be saved.'
  read -rs "pinecone_key?Pinecone API key: "
  echo
fi
if [[ "$pinecone_key" != pcsk_* ]]; then
  echo 'The supplied value is not a Pinecone API key.' >&2
  exit 1
fi

PINECONE_API_KEY="$pinecone_key" python3 cloud/pinecone_import.py \
  --chunks "output/$package/chunks.jsonl" \
  --documents "output/$package/documents.jsonl" \
  --namespace phase1 \
  --state "output/cloud/$state" \
  --source-type reference_book

curl -fsS -X POST \
  'https://ecclesia-phase1-zwrd0cz.svc.aped-4627-b74a.pinecone.io/describe_index_stats' \
  -H "Api-Key: $pinecone_key" \
  -H 'Content-Type: application/json' \
  --data '{}' \
  -o "output/cloud/$stats"
echo 'Verified Pinecone index statistics:'
python3 -m json.tool "output/cloud/$stats"

unset pinecone_key
echo "$label Pinecone import complete. You may close this window."
if [[ -t 0 ]]; then
  read -r '?Press Return to close.'
fi
