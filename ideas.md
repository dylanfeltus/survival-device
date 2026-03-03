# Ideas: Survival AI UI Flow (Pip-Boy Inspired)

## Vision
A compact, legible, tactical interface built for glanceability in field conditions. The screen language should prioritize **contrast, status clarity, and one-hand navigation**.

## Core Screen Set

### 1) Boot / Wake Screen
- Big title: `SURVIVAL AI`
- Status ticker: battery %, solar input, storage, model ready
- Button hint row: `OK=Start | BACK=Shutdown | RIGHT=Help`
- Auto-timeout to home after setup steps

### 2) Home / Status Dashboard
- Top-left: Time + temperature from onboard sensor
- Center panel (large numbers): `MODE: OFFLINE`
- Sub-panels (2 columns):
  - **Battery**: % and estimated runtime
  - **Storage**: source pack, index version
  - **Audio**: on/off indicator
- Right rail shortcuts: `QUERY`, `MAP`, `SUPPLY`, `SHELTER`

### 3) Query Screen (Chat)
- Query input row (on rotary + enter): voice wake alternative
- Last answer card with bullet summary + citation chips
- `SWIPE/UP` cycles previous answers
- Footer actions:
  - `PLAY` = read aloud (if `audio_enabled`)
  - `COPY` = save to favorites
  - `SRC` = expanded sources panel

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

## Interaction Model (Buttons/Controls)

Assumed controls: `UP`, `DOWN`, `LEFT`, `RIGHT`, `ENTER`, `BACK`

### Global mapping
- `UP/DOWN`: navigate menu lists / scroll text
- `LEFT/RIGHT`: tabs and screens
- `ENTER`: confirm / send
- `BACK`: previous screen or cancel
- `SHORT HOLD ENTER (1s)`: open context menu

### Home
- `RIGHT`: open Query
- `LEFT`: open Logs/Diagnostics
- `UP`: emergency quick actions
- `DOWN`: last answer

### Query
- `ENTER`: speak/send dictated/typed query
- `RIGHT`: toggle wake-word mode
- `LEFT`: open source citations
- `BACK`: return home

### Checklists
- `ENTER`: run checklist step
- `DOWN`: next step
- `BACK`: exit checklist (with confirm)

## Citations in UI
- Every answer shows small source chips `[1][2][3]`
- Selecting a chip opens mini drawer:
  - Title
  - Source + license
  - Local path/URL
  - Ingest timestamp + hash

## Visual Language
- **Color:** `#0a4d2b` (bg), `#4eb56d` (primary), `#f5f59a` (warn), `#f7f7f7` (text)
- **Typography:** uppercase for command headers, lowercase for body
- **Grid:** 8px rhythm, heavy card borders, sparse glow accents
- **Motion:** minimal; no expensive transitions to preserve battery

## v1 Defaults to Keep it Safe
- No automatic online query fallback
- No hidden data upload
- Explicit “Source required for each claim” rule in renderer
- No geolocation unless user manually toggles
- No microphone auto-listen by default (`wake_word: false`)

