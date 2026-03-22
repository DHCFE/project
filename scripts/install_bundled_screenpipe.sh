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

python3 - <<'PY'
from time_thief_hunter.vendor_screenpipe import install_bundled_binary, vendored_binary_path

binary = vendored_binary_path()
if binary is None:
    raise SystemExit("screenpipe binary not found after build")

target = install_bundled_binary(binary)
if target is None:
    raise SystemExit("failed to install bundled screenpipe")

print(f"installed bundled screenpipe -> {target}")
PY
