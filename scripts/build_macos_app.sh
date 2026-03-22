#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! python3 - <<'PY' >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("PyInstaller") else 1)
PY
then
  echo "PyInstaller not found. Install it with: python3 -m pip install pyinstaller"
  exit 1
fi

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name TimeThiefHunter \
  --osx-bundle-identifier com.dhcfe.timethiefhunter \
  --paths "$ROOT" \
  --distpath dist/macos \
  --workpath build/pyinstaller \
  --specpath build/pyinstaller \
  --add-data "$ROOT/time_thief_hunter/ui:time_thief_hunter/ui" \
  --add-data "$ROOT/time_thief_hunter/prompts:time_thief_hunter/prompts" \
  --add-data "$ROOT/time_thief_hunter/bin:time_thief_hunter/bin" \
  --add-data "$ROOT/THIRD_PARTY_NOTICES.md:." \
  --collect-submodules webview \
  --collect-data webview \
  --hidden-import webview.platforms.cocoa \
  "$ROOT/time_thief_hunter/__main__.py"

echo "built macOS app -> dist/macos/TimeThiefHunter.app"
