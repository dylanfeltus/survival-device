# Survival AI Device v1 (Offline MVP)

## Project Objective
Build an **offline-first Survival AI device** on Orange Pi Zero 2W 4GB that can answer field-relevant questions from preloaded manuals, maps, checklists, and prep plans without cloud connectivity. v1 focuses on resilience: power-aware hardware, predictable local inference, auditable content provenance, and safe defaults for deployment readiness.

This scaffold provides architecture docs, startup scripts, ingestion + retrieval tooling, and a local chat CLI around a local LLM + vector retrieval pipeline.

---

## 1) Target Hardware (v1)

- **Compute:** Orange Pi Zero 2W 4GB (Amlogic A53 quad-core, eMMC/SD storage)
- **Display:** 480x320/800x480 LCD via HDMI or SPI framebuffer-compatible panel
- **Input:** Rotary encoder + 2–5 GPIO buttons (or membrane keypad equivalent)
- **Audio:** USB/class D headphone amp + speaker (optional)
- **Storage:** 32GB+ microSD
- **Power:** UPS HAT (lithium battery + protection board) + optional solar charge controller
- **Power strategy:** Low-power offline operation with batched workload scheduling

### Recommended Bill of Materials (starter)
- Orange Pi Zero 2W 4GB
- 5V/4A UPS HAT (power management + battery sense)
- 12V→5V DC-DC converter for panel/audio branch if needed
- 20W–40W solar panel + MPPT buck
- 7Ah LiFePO4 or similar pack (chemistry matched to UPS)
- Enclosure with airflow and thermal path

---

## 2) Architecture (v1 MVP)

### Logical Stack

1. **Ingestion Layer**
   - Source docs ingested from local folders described by JSON/CSV manifest
   - Normalization + chunking + metadata extraction + local checksums
   - Embeddings generated from a local model or deterministic fallback encoder
2. **Storage Layer**
   - Source registry + chunk metadata in lightweight local DB/JSON index
   - Vector index persisted on disk for restart-safe retrieval
3. **Retrieval Layer (RAG)**
   - `chat.py` performs cosine retrieval over top-k chunks from local index
   - Each chunk carries title/section/license/source URL/path
4. **Generation Layer (LLM)**
   - Local binary inference process (configurable) called with prompt + retrieved context
   - Context size controlled via `context_k`
5. **Device Services Layer**
   - Scripts for setup, display self-test, health checks, and benchmarking
6. **Safety & Audit Layer**
   - Source licenses tracked per chunk
   - All answers include references back to chunk metadata

### Offline Pipeline

- No live web/network calls during inference by default.
- Inference path:
  `User query -> top-k retrieval -> compose prompt + context + citation template -> local LLM -> response`
- Optional wake-word and audio can be enabled for voice-first usage.

---

## 3) Safety & Legal Sourcing Strategy

**Priority policy (strict):**
1. **Public domain first** (US govt docs, disaster guidance where permitted, CC0 sources).
2. **Permissive licenses** (CC-BY/CC-BY-SA/CC0 with attribution).
3. **Commercial or uncertain licenses** only with explicit packaging permission + manual legal review.

### Metadata Required per source
Each ingested document must include:
- `title`
- `source`
- `source_url` (if present in offline archive index)
- `license` (exact text)
- `license_notes`
- `license_url` (if available)
- `ingested_at`, `sha256`, `language`, `domain`

### Runtime Safety
- No model output is treated as official authority.
- UI must display: **“Source-cited only. Verify with local emergency channels when possible.”**
- Citations are inserted from retrieval results (ID, source, and section).

---

## 4) Power Budget (Orange Pi Zero 2W design target)

### Assumptions
- SoC idle at ~1.2W (screen off)
- Average CPU inferencing while idle polling: +2.0W
- LCD panel + backlight: 1.5W
- Audio amp + speaker playback: 0.5W average when active
- UPS conversion losses: +10%

### Typical Draw (W)
- **Idle baseline (interactive standby):**
  - SoC 1.2W + display 1.5W + overheads 0.5W + losses 0.3W = **3.5W**
- **Active query + local inference burst:**
  - SoC 3.0W + display 1.5W + overhead 1.0W + audio 0.5W + losses 0.5W = **6.5W**

### Runtime estimate
For a 12V 7Ah battery, usable energy (conservative 80%):
- 12V × 7Ah × 0.8 = **67.2Wh**

- **Idle runtime:** 67.2Wh / 3.5W ≈ **19.2h**
- **Active average 20% of time:**
  - Effective power = 0.8×3.5 + 0.2×6.5 = 4.1W
  - Runtime ≈ 16.4h

### Solar replenishment (target)
- 20W panel, 4h effective sun/day, 70% conversion efficiency:
  - 20×4×0.7 = **56Wh/day** theoretical input
- Net daily run profile example:
  - 16h active-usage equivalent at 4.1W = 65.6Wh/day
  - So panel alone is not enough; schedule longer charging windows and intermittent use.

---

## 5) Build Phases

### Phase 1 — Prototype (v1)
Goal: prove offline ingestion + retrieval + CLI chat.

- Single user can run setup, ingest public docs, and ask questions through `scripts/chat.py`.
- Citation format is present and displayed in CLI.
- Display/test scripts run and fail safely on non-embedded hosts.
- Hardware dependencies are feature-checked (not hard-required on desktop dev).

### Phase 2 — Alpha
Goal: run on Orange Pi Zero 2W with physical UI.

- Test GPIO button mapping + framebuffer splash/status
- Local benchmarks tracked (`scripts/benchmark.sh`)
- UPS status polling and graceful low-power mode toggles
- Source manifest contains legal/compliance metadata for all docs

### Phase 3 — Crowdfunding Readiness
Goal: production-safe packaging.

- Signed installer + reproducible provisioning checklist
- Preloaded content packs with versioned source manifest
- Recovery tools + logs + battery fault handling
- Performance envelope docs, failure modes, and support playbook

---

## 6) Repository Layout (v1)

```text
survival-device/
├── README.md
├── ideas.md
├── config/
│   └── default.json
├── scripts/
│   ├── setup.sh
│   ├── ingest_booklist.py
│   ├── chat.py
│   ├── benchmark.sh
│   └── test-display.sh
└── data/
    └── README.md
```

## 7) Quick Start

```bash
cd /Users/claudia/Code/survival-device
chmod +x scripts/*.sh
cp config/default.json config/local.json   # optional override
./scripts/setup.sh
```

Ingest source list and build index:

```bash
python3 scripts/ingest_booklist.py --sources data/booklist.json --index-path data/index
```

Run chat:

```bash
python3 scripts/chat.py "What should I do if I see signs of heat exhaustion?"
```

---

## 8) Assumptions

- Device uses a local LLM binary already present or installed separately.
- No network access required during normal operation.
- Source files are prepared offline and copied into `sources_directory` before indexing.
- Citation fidelity is preferred over model creativity for v1.
- This scaffold is opinionated toward resilience, not maximum model quality.

