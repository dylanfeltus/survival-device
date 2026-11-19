#!/usr/bin/env bash
set -euo pipefail

# Survival AI Device - Setup Script
# Gets you from zero to ready in under 5 minutes

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Options:
#   --download-model[=NAME]  also fetch a GGUF model (NAME: qwen3-1.7b (default), gemma3-1b, qwen3-0.6b)
#   --reindex                rebuild data/index/index.json even if it already exists
DOWNLOAD_MODEL=""
REINDEX=0
for arg in "$@"; do
    case "$arg" in
        --download-model) DOWNLOAD_MODEL="qwen3-1.7b" ;;
        --download-model=*) DOWNLOAD_MODEL="${arg#*=}" ;;
        --reindex) REINDEX=1 ;;
        -h|--help) sed -n 2,12p "$0"; exit 0 ;;
        *) echo "Unknown option: $arg"; exit 2 ;;
    esac
done

log() { printf "\033[0;32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[0;33m!\033[0m %s\n" "$*"; }
error() { printf "\033[0;31m✗\033[0m %s\n" "$*"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Survival AI Device - Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Check Python version
log "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    error "python3 not found. Please install Python 3.10 or later."
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    error "Python $PYTHON_VERSION found. Python 3.10+ required."
fi

log "Python $PYTHON_VERSION detected"

# 2. Create virtualenv if it doesn't exist
if [ ! -d "${ROOT_DIR}/venv" ]; then
    log "Creating virtual environment..."
    python3 -m venv "${ROOT_DIR}/venv"
    log "Virtual environment created at ${ROOT_DIR}/venv"
else
    log "Virtual environment already exists"
fi

# 3. Install minimal Python dependencies
log "Installing minimal dependencies..."
source "${ROOT_DIR}/venv/bin/activate"

# Core dependencies (none required for basic hash-based mode)
# Optional: sentence-transformers for semantic embeddings
pip install --upgrade pip -q

echo ""
echo "  Optional dependencies:"
echo "  • sentence-transformers - For semantic search (requires ~500MB)"
echo "    Install with: pip install sentence-transformers"
echo ""

# 4. Create required directories
log "Creating required directories..."
mkdir -p "${ROOT_DIR}/data/index"
mkdir -p "${ROOT_DIR}/data/sources"
mkdir -p "${ROOT_DIR}/data/manifests"
mkdir -p "${ROOT_DIR}/data/runtime"
mkdir -p "${ROOT_DIR}/logs"
mkdir -p "${ROOT_DIR}/models"

# 5. Check for llama.cpp / llama-cli
log "Checking for llama.cpp..."
if command -v llama-cli &> /dev/null; then
    LLAMA_VERSION=$(llama-cli --version 2>&1 | head -n1 || echo "unknown")
    log "llama-cli found: $LLAMA_VERSION"
elif command -v llama &> /dev/null; then
    log "llama executable found"
elif [ -f "/opt/llama.cpp/llama-cli" ]; then
    log "llama-cli found at /opt/llama.cpp/llama-cli"
else
    warn "llama.cpp not found in PATH"
    echo ""
    echo "  To install llama.cpp:"
    echo "  1. Clone: git clone https://github.com/ggerganov/llama.cpp"
    echo "  2. Build: cd llama.cpp && make"
    echo "  3. Install: sudo make install (or add to PATH)"
    echo ""
    echo "  Alternatively, download pre-built binaries:"
    echo "  https://github.com/ggerganov/llama.cpp/releases"
    echo ""
fi

# 6. Basic self-test
log "Running self-tests..."

# Test Python imports
SURV_ROOT="$ROOT_DIR" python3 - <<'PY'
import sys
import json
import os
from pathlib import Path

errors = []

# Test basic imports
try:
    import hashlib
    import re
    import argparse
except ImportError as e:
    errors.append(f"Missing standard library: {e}")

# Test script imports
sys.path.insert(0, str(Path(os.environ["SURV_ROOT"]) / "scripts"))
try:
    import ingest_booklist
    import chat
except Exception as e:
    errors.append(f"Script import failed: {e}")

if errors:
    print("\033[0;31m✗\033[0m Self-test failed:")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("\033[0;32m✓\033[0m All imports successful")
PY

if [ $? -ne 0 ]; then
    error "Self-test failed. Check Python installation."
fi

# 7. Build the search index (generated locally; not committed to git)
INDEX_PATH="${ROOT_DIR}/data/index/index.json"
if [ "$REINDEX" -eq 1 ] || [ ! -f "$INDEX_PATH" ]; then
    log "Building search index from the core survival pack..."
    (cd "$ROOT_DIR" && python3 scripts/ingest_booklist.py \
        --sources data/manifests/core-survival.json \
        --sources-directory data/sources \
        --index-path data/index/index.json)
else
    log "Search index already exists (use --reindex to rebuild)"
fi

# 8. Optional: download the recommended GGUF model
if [ -n "$DOWNLOAD_MODEL" ]; then
    "${ROOT_DIR}/scripts/download_model.sh" "$DOWNLOAD_MODEL" --set-config || warn "Model download failed; offline retrieval mode still works."
else
    echo ""
    echo "  LLM model (optional): ./scripts/download_model.sh   # Qwen3 1.7B Q4_K_M -> models/"
    echo ""
fi

# 9. Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎉 Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Quick Start:"
echo ""
echo "  1. (Re)ingest content after adding sources:"
echo "     ./scripts/setup.sh --reindex"
echo ""
echo "  2. Test offline search:"
echo "     python3 scripts/chat.py --offline \"How do I purify water?\""
echo ""
echo "  3. Run with LLM (requires llama.cpp + ./scripts/download_model.sh):"
echo "     python3 scripts/chat.py \"How do I start a fire?\""
echo ""
echo "  4. Launch UI (framebuffer or terminal):"
echo "     python3 scripts/ui.py"
echo ""
echo "  Project directory: $ROOT_DIR"
echo "  Virtual environment: source venv/bin/activate"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
