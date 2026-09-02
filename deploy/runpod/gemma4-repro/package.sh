#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/env.sh"
archive="${1:-$(dirname "$BUNDLE_ROOT")/runpod-gemma4-repro-20260621-gemma26.tar.gz}"
checksum_file="$BUNDLE_ROOT/SHA256SUMS"
(
  cd "$BUNDLE_ROOT"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 shasum -a 256 > "$checksum_file"
)
python3 "$BUNDLE_ROOT/validate_bundle.py" "$BUNDLE_ROOT"
tar -C "$(dirname "$BUNDLE_ROOT")" -czf "$archive" "$(basename "$BUNDLE_ROOT")"
archive_dir="$(cd "$(dirname "$archive")" && pwd)"
archive_name="$(basename "$archive")"
(
  cd "$archive_dir"
  shasum -a 256 "$archive_name" > "$archive_name.sha256"
)
echo "OK: $archive"
