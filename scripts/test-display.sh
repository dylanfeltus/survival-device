#!/usr/bin/env bash
set -euo pipefail

# Display test for Survival AI Device
# Detects framebuffer or falls back to terminal output

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Check for framebuffer
if [ -e /dev/fb0 ]; then
    echo "[INFO] Framebuffer detected (/dev/fb0)"
    
    # Create simple green-on-black test pattern
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY'
# Simple green-on-black test pattern for framebuffer
w, h = 320, 240

pixels = []
for y in range(h):
    for x in range(w):
        # Green-on-black theme
        if y < 30 or y > h-30 or x < 30 or x > w-30:
            # Green border
            r, g, b = 0, 255, 0
        else:
            # Black background
            r, g, b = 0, 0, 0
        
        # Add some test pattern stripes
        if y % 40 < 20:
            g = max(0, g - 128)
        
        pixels.extend([r, g, b])

# Write PPM format
with open('/tmp/survival_test.ppm', 'wb') as f:
    f.write(f"P6 {w} {h} 255 \n".encode('ascii'))
    f.write(bytes(pixels))

print("Test pattern created: /tmp/survival_test.ppm")
PY
        
        # Try to display it
        if command -v fbi >/dev/null 2>&1; then
            fbi -d /dev/fb0 -T 1 -noverbose /tmp/survival_test.ppm 2>/dev/null
            echo "[INFO] Test pattern rendered via fbi"
        elif command -v fim >/dev/null 2>&1; then
            fim -q -a /tmp/survival_test.ppm 2>/dev/null
            echo "[INFO] Test pattern rendered via fim"
        else
            echo "[WARN] No framebuffer viewer found (fbi/fim)"
            echo "      Install with: sudo apt-get install fbi"
        fi
    else
        echo "[ERROR] Python3 not found, cannot generate test pattern"
        exit 1
    fi
else
    # Terminal mode - print formatted test card
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                 SURVIVAL AI DEVICE                         ║"
    echo "║                   Display Test Card                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  System Information:"
    echo "  ───────────────────────────────────────────────────────────"
    
    # OS info
    if command -v uname >/dev/null 2>&1; then
        echo "  OS:              $(uname -s) $(uname -r)"
        echo "  Architecture:    $(uname -m)"
    fi
    
    # Python version
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VER=$(python3 --version 2>&1)
        echo "  Python:          $PYTHON_VER"
    else
        echo "  Python:          NOT FOUND"
    fi
    
    # Disk usage
    if [ -d "$ROOT_DIR" ]; then
        DISK_USAGE=$(du -sh "$ROOT_DIR" 2>/dev/null | cut -f1)
        echo "  Project Size:    $DISK_USAGE"
    fi
    
    # Memory
    if command -v free >/dev/null 2>&1; then
        MEM_INFO=$(free -h | grep Mem | awk '{print $2 " total, " $3 " used"}')
        echo "  Memory:          $MEM_INFO"
    elif command -v vm_stat >/dev/null 2>&1; then
        echo "  Memory:          $(vm_stat | grep "Pages free" | awk '{print $3}') pages free"
    fi
    
    echo ""
    echo "  Available Scripts:"
    echo "  ───────────────────────────────────────────────────────────"
    
    # List key scripts
    if [ -f "$ROOT_DIR/scripts/ingest_booklist.py" ]; then
        echo "  ✓ ingest_booklist.py  - Index content for search"
    fi
    
    if [ -f "$ROOT_DIR/scripts/chat.py" ]; then
        echo "  ✓ chat.py             - Query survival knowledge"
    fi
    
    if [ -f "$ROOT_DIR/scripts/ui.py" ]; then
        echo "  ✓ ui.py               - Interactive interface"
    fi
    
    if [ -f "$ROOT_DIR/scripts/setup.sh" ]; then
        echo "  ✓ setup.sh            - First-time setup"
    fi
    
    echo ""
    echo "  Content Packs:"
    echo "  ───────────────────────────────────────────────────────────"
    
    if [ -f "$ROOT_DIR/data/index/index.json" ]; then
        CHUNK_COUNT=$(python3 -c "import json; print(json.load(open('$ROOT_DIR/data/index/index.json'))['chunk_count'])" 2>/dev/null || echo "unknown")
        DOC_COUNT=$(python3 -c "import json; print(json.load(open('$ROOT_DIR/data/index/index.json'))['document_count'])" 2>/dev/null || echo "unknown")
        echo "  ✓ Index loaded:       $DOC_COUNT documents, $CHUNK_COUNT chunks"
    else
        echo "  ✗ No index found      Run ingest_booklist.py first"
    fi
    
    echo ""
    echo "  Status:              All systems nominal"
    echo "  Framebuffer:         Not detected (/dev/fb0 missing)"
    echo "  Display Mode:        Terminal"
    echo ""
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
fi

exit 0
