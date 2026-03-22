#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMPDIR="$(mktemp -d /tmp/screenpipe-vendor.XXXXXX)"
UPSTREAM="${1:-https://github.com/mediar-ai/screenpipe.git}"
BRANCH="${2:-main}"

git clone --depth 1 --branch "$BRANCH" "$UPSTREAM" "$TMPDIR"
mkdir -p "$ROOT/third_party/screenpipe"
rsync -a --delete --exclude '.git' "$TMPDIR"/ "$ROOT/third_party/screenpipe"/

echo "updated vendored screenpipe from $UPSTREAM ($BRANCH)"
