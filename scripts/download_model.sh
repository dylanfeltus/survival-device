#!/usr/bin/env bash
set -euo pipefail

# Download a recommended GGUF model for llama.cpp into the configured models folder.
#
# Usage: scripts/download_model.sh [MODEL] [--set-config]
#   MODEL:
#     qwen3-1.7b  (default) Qwen3 1.7B Q4_K_M  - best quality that fits 4GB (~1.9GB RAM in use)
#     gemma3-1b             Gemma 3 1B Q4_K_M  - lighter fallback
#     qwen3-0.6b            Qwen3 0.6B Q4_K_M  - speed option
#   --set-config  point "model_path" in config/default.json at the downloaded file
#
# The target folder is the directory of "model_path" in config/default.json
# (relative paths are resolved against the repo root; default: models/).
#
# Needs internet once; everything after that is offline.
# TODO(verify): the Hugging Face repo/file names below could not be checked from the
# environment this was written in. If a download 404s, browse the repo on huggingface.co
# and pass the correct URL via MODEL_URL=... (and MODEL_FILE=...).

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CFG="${ROOT_DIR}/config/default.json"

MODEL="qwen3-1.7b"
SET_CONFIG=0
for arg in "$@"; do
  case "$arg" in
    --set-config) SET_CONFIG=1 ;;
    -h|--help) sed -n 2,20p "$0"; exit 0 ;;
    -*) echo "Unknown option: $arg"; exit 2 ;;
    *) MODEL="$arg" ;;
  esac
done

case "$MODEL" in
  qwen3-1.7b)
    DEFAULT_FILE="Qwen3-1.7B-Q4_K_M.gguf"
    DEFAULT_URL="https://huggingface.co/unsloth/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf" ;;
  gemma3-1b)
    DEFAULT_FILE="gemma-3-1b-it-Q4_K_M.gguf"
    DEFAULT_URL="https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf" ;;
  qwen3-0.6b)
    DEFAULT_FILE="Qwen3-0.6B-Q4_K_M.gguf"
    DEFAULT_URL="https://huggingface.co/unsloth/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf" ;;
  *)
    echo "Unknown model '$MODEL'. Choose: qwen3-1.7b, gemma3-1b, qwen3-0.6b"; exit 2 ;;
esac

FILE="${MODEL_FILE:-$DEFAULT_FILE}"
URL="${MODEL_URL:-$DEFAULT_URL}"

# Resolve the models folder from config model_path (fallback: models/).
MODELS_DIR="$(python3 - "$CFG" "$ROOT_DIR" <<'PY'
import json, sys
from pathlib import Path
cfg_path, root = Path(sys.argv[1]), Path(sys.argv[2])
try:
    mp = str(json.loads(cfg_path.read_text()).get("model_path", "")).strip()
except Exception:
    mp = ""
p = Path(mp).expanduser() if mp else Path("models/x.gguf")
if not p.is_absolute():
    p = root / p
print(p.parent)
PY
)"

mkdir -p "$MODELS_DIR"
DEST="${MODELS_DIR}/${FILE}"

if [ -f "$DEST" ]; then
  echo "✓ Already present: $DEST"
else
  echo "Downloading $MODEL"
  echo "  from: $URL"
  echo "  to:   $DEST"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail --retry 3 -C - -o "${DEST}.part" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -c -O "${DEST}.part" "$URL"
  else
    echo "✗ Need curl or wget."; exit 1
  fi
  # Sanity check: GGUF files start with the ASCII magic "GGUF".
  if [ "$(head -c 4 "${DEST}.part")" != "GGUF" ]; then
    echo "✗ Downloaded file is not a GGUF model (wrong URL or an HTML error page). Kept as ${DEST}.part"
    exit 1
  fi
  mv "${DEST}.part" "$DEST"
  echo "✓ Saved $DEST"
fi

if [ "$SET_CONFIG" -eq 1 ]; then
  python3 - "$CFG" "$ROOT_DIR" "$DEST" <<'PY'
import json, sys
from pathlib import Path
cfg_path, root, dest = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
cfg = json.loads(cfg_path.read_text())
try:
    value = dest.resolve().relative_to(root.resolve()).as_posix()
except ValueError:
    value = str(dest)
cfg["model_path"] = value
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
print(f"✓ config/default.json model_path = {value}")
PY
else
  echo ""
  echo "If this is not the file named by model_path in config/default.json, re-run with --set-config"
  echo "or edit model_path by hand. Leave model_path empty for retrieval-only mode."
fi
