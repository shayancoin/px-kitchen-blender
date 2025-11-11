#!/bin/bash
set -euo pipefail

ROOT_DIR="/Users/shayanbozorgmanesh/Developer/PX-blender"
BLENDER_BIN=${BLENDER_BIN:-"/Applications/Blender.app/Contents/MacOS/Blender"}
SCRIPT_PATH="$ROOT_DIR/scripts/web_kitchen_bundles.py"
OUT_DIR="${1:-$ROOT_DIR/web_kitchen_bundles_png}"
MODE="${MODE:-preview}"

if [[ ! -x "$BLENDER_BIN" ]]; then
  echo "Blender binary not found at $BLENDER_BIN" >&2
  exit 1
fi

exec "$BLENDER_BIN" \
  --background \
  --factory-startup \
  --disable-autoexec \
  -P "$SCRIPT_PATH" -- \
  --mode "$MODE" \
  --format PNG \
  --quality 100 \
  --out "$OUT_DIR"


