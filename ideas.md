# Ideas: Survival AI UI Flow (Pip-Boy Inspired)

## Vision
A compact, legible, tactical interface built for glanceability in field conditions. The screen language should prioritize **contrast, status clarity, and one-hand navigation**.

---

## IMPLEMENTED: Terminal UI v1 (scripts/ui.py)

### Screen Layout (320x240 = ~40 cols x 15 rows)
```
┌─[SURVIVE]─[NAV]─[MED]─[TECH]─[IDX]─┐  ← Tab navigation bar
│                                       │
│ > query text here                     │  ← Query input line
│                                       │
│ Answer text streams here line by      │  ← Scrollable answer area
│ line with [1] citation markers        │     with citations
│                                       │
│ [1] Title - Source                    │  ← Citation list
│                                       │
├───────────────────────────────────────┤
│ ■ BATT 78%  ■ NORMAL  ■ 14:32       │  ← Status bar
└───────────────────────────────────────┘
```

### Implemented Key Bindings
- **Enter** — Submit query (when text entered)
- **Left/Right Arrow** — Switch between tabs (SURVIVE, NAV, MED, TECH, INDEX)
- **Up/Down Arrow** — Scroll answer area (when not in input mode)
- **Tab** — Toggle between query input mode and answer scroll mode
- **Page Up** — View older items in history
- **Page Down** — View newer items in history
- **Ctrl+C or q** — Quit application

### Features Implemented
1. **Tab Navigation** — 5 category tabs at top, left/right arrow to switch
2. **Query Input** — Type query, shows "thinking..." during processing
3. **Answer Display** — Scrollable area with citations marked [1], [2]...
4. **Citation Display** — Full citation list below answer (title, source)
5. **History** — Last 10 Q&A pairs kept, navigate with Page Up/Down
6. **Status Bar** — Shows battery %, power mode, time, model status
7. **Green Phosphor Theme** — Green on black, bold highlights, yellow warnings
8. **Startup Splash** — 2-second SURV-AI loading screen
9. **Graceful Fallbacks** — Simple print mode if curses unavailable
10. **Error Handling** — Shows errors in UI if chat backend fails

### Integration
- Calls `scripts/chat.py --json "query"` via subprocess
- Parses JSON response for answer, citations, confidence
- Reads battery state from `data/runtime/state.json` if available
- Configuration loaded from `scripts/ui_config.json`

### Color Scheme
- **Primary text:** Green (curses.COLOR_GREEN)
- **Dim text:** Dark green
- **Highlights:** Bright green + bold (active tab, query input)
- **Warnings:** Yellow (thinking state, errors)
- **Status bar:** Reverse video (green background, black text)
- **Background:** Black

### Config (scripts/ui_config.json)
```json
{
  "refresh_rate_ms": 500,
  "history_max": 10,
  "scroll_lines": 3,
  "tab_names": ["SURVIVE", "NAV", "MED", "TECH", "INDEX"],
  "color_primary": "green",
  "color_dim": "dark_green",
  "color_warn": "yellow",
  "splash_duration_s": 2
}
```

### Usage
```bash
cd /path/to/survival-device
python3 scripts/ui.py
```

Works in:
- Standard terminal (macOS Terminal, iTerm2, etc.)
- Linux TTY / framebuffer console
- SSH sessions
- Falls back to simple print mode if curses unavailable

---

## FUTURE IDEAS (Not Yet Implemented)

### 2) Home / Status Dashboard
- Top-left: Time + temperature from onboard sensor
- Center panel (large numbers): `MODE: OFFLINE`
- Sub-panels (2 columns):
  - **Battery**: % and estimated runtime
  - **Storage**: source pack, index version
  - **Audio**: on/off indicator
- Right rail shortcuts: `QUERY`, `MAP`, `SUPPLY`, `SHELTER`

### 4) Emergency Checklist Category View
- Categories as quick tiles:
  - **Injury / Medical**
  - **Water / Food / Heat**
  - **Navigation**
  - **Signaling / Safety**
  - **Repair / Energy**
  - **Prep / Supplies**
- Select category auto-filters search over chunks with citation tags
- Long-press on item opens compact 5-step checklist

### 5) Sources / Compliance Screen
- Shows top 3 active source docs with license badges
- License colors:
  - Green = public domain
  - Amber = permissive
  - Red = restricted / needs verify
- Footer warns when using non-PD docs above threshold

### 6) Benchmark / Diagnostics Screen
- Live cards:
  - query latency
  - top-k retrieval count
  - index size
  - temperature / throttle status
  - power sample (from sensor hook)
- Trigger from hold-right button for 2s

## Citations in UI (Implemented)
- Every answer shows citation markers [1], [2], [3]
- Full citation list displays below answer with:
  - Title
  - Source
  - Confidence score (future: add license, URL)

## Visual Language (Implemented)
- **Color:** Green on black (classic phosphor terminal)
- **Typography:** Mixed case, bold for highlights
- **Layout:** Box drawing characters for clean borders
- **Motion:** Minimal; instant screen updates to preserve battery

## v1 Safety Defaults (Maintained)
- No automatic online query fallback
- No hidden data upload
- Explicit citation display for every answer
- No geolocation
- No microphone auto-listen (`wake_word: false` in config)

