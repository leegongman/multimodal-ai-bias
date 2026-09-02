#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${SHADOW_REVIEW_PORT:-8765}"
URL="http://127.0.0.1:${PORT}/data/shadow-private/pending-v1/review.html"

cd "$ROOT_DIR"
echo "Shadow review server: $URL"
echo "Keep this window open while reviewing. Press Control-C to stop."
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory .
