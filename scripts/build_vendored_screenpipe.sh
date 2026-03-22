#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo not found"
  exit 1
fi

cargo build \
  --manifest-path third_party/screenpipe/Cargo.toml \
  -p screenpipe-engine \
  --bin screenpipe \
  --profile release-dev

echo "built vendored screenpipe"
