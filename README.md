# Survival AI Device

An offline-first survival knowledge system for Orange Pi Zero 2W. Ask questions about water purification, fire starting, first aid, navigation, and more — all without internet connectivity.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/dylanfeltus/survival-device.git
cd survival-device

# 2. Run setup (also builds the search index in data/index/index.json)
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. (Re)ingest survival content — only needed after adding/changing sources
python3 scripts/ingest_booklist.py \
  --sources data/manifests/core-survival.json \
  --sources-directory data/sources \
  --index-path data/index/index.json

# 4. Ask a question (offline mode)
python3 scripts/chat.py --offline "How do I purify water in the field?"

# 5. Launch UI (optional)
python3 scripts/ui.py
```

That's it. You now have a working offline survival knowledge system.

---

## Hardware

**Target Platform:** Orange Pi Zero 2W, 4GB RAM, 4× Cortex-A53 (Allwinner H618)

### Bill of Materials

| Component | Part | Notes |
|-----------|------|-------|
| SBC | Orange Pi Zero 2W, **4GB** | Header ships unpopulated: solder or press-fit a 2×20 (40-pin) 2.54 mm header. [OrangePi.org](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/details/Orange-Pi-Zero-2W.html) |
| Storage | 32GB+ microSD (Class 10 / A1) | Room for the OS, index and a ~1–2 GB GGUF model |
| Power / UPS | SeenGreat Pi Zero UPS HAT (B), Rev 1.5 | Spring pogo pins under the Pi; USB-C input; INA219 battery monitor on I2C at **0x43**; **built-in MPPT solar charger**. [Wiki](https://seengreat.com/wiki/175/pi-zero-ups-hat-b) |
| Battery | Flat 3.7 V LiPo pouch cell | 2-pin connector on the HAT. ⚠️ Check polarity against the HAT silkscreen before plugging in. Capacity: your choice (TODO: record it here) |
| Solar (opt) | 5–24 V panel → HAT terminal block | No separate MPPT controller needed. Set the HAT's DIP switch to match the panel's **Vmp**, with **only ONE position ON** (table on the SeenGreat wiki) |
| Main display | Generic red-PCB 2.8" SPI TFT, 240×320, resistive touch | Probably ILI9341 + XPT2046 (⚠️ confirm). Jumper-wired, not a HAT. See [docs/wiring.md](docs/wiring.md) |
| Status display | Small round SPI TFT, blue breakout | Probably GC9A01 240×240 (⚠️ confirm). Shows battery %, charging, mode |
| Input | Rotary encoder module with push button | Pins CLK, DT, SW, +, GND. Power from **3.3 V** |
| Antenna | WiFi antenna | On the board's antenna connector |
| Misc | Jumper wires, M2.5 standoffs for the HAT | Standoff height matters for pogo-pin contact |

**Desktop Development:** Runs on any Linux/macOS/Windows system with Python 3.10+

---

## Hardware bring-up

Do this in order, verifying each step before the next. Pinouts, overlays and bus numbers
are in [docs/wiring.md](docs/wiring.md).

1. **Flash the OS.** Write Armbian or the official Orange Pi Debian image *for the Orange Pi
   Zero 2W* to the microSD card (balenaEtcher / `dd`). Before first boot, set up WiFi if
   the image supports it (e.g. via its first-boot config). Otherwise use a serial console
   on header pins 8/10 (UART0), or HDMI + keyboard, for the first login.
2. **First boot on USB-C, SSH over WiFi.** Power the bare board from USB-C, with **no HAT, no
   displays**. Join WiFi (`nmtui` on most images), find the IP, then `ssh` in. Update:
   `sudo apt update && sudo apt upgrade`.
3. **Software check before any wiring.**
   ```bash
   sudo apt install -y git python3 python3-venv i2c-tools python3-libgpiod python3-pil python3-spidev
   git clone https://github.com/dylanfeltus/survival-device.git && cd survival-device
   ./scripts/setup.sh                 # builds the search index
   ./scripts/setup.sh --reindex       # re-ingest (do this after adding sources)
   python3 scripts/chat.py --offline "How do I purify water?"
   ```
   Retrieval-only mode must work here before any hardware is added. Optional: install
   llama.cpp and run `./scripts/download_model.sh` (see [LLM models](#llm-models)).
   (If `python3-spidev` isn't packaged on your image, `pip install spidev` instead.)
4. **Mount the UPS HAT.** `sudo poweroff` and unplug USB-C. Then:
   1. HAT power switch **OFF**.
   2. Seat the Pi on the HAT and **fasten the standoffs**. The pogo pins must press firmly and
      evenly on the header's solder joints. Standoffs that are too tall cause intermittent
      contact, and the INA219 then "disappears".
   3. **Connect the LiPo pouch cell** to the HAT's 2-pin connector (⚠️ check polarity).
   4. HAT switch **ON**. The board should boot from battery. USB-C now goes into the **HAT**.
   5. (Solar) Set the DIP switch to your panel's Vmp, with only one position ON, *before*
      connecting the panel.
5. **Enable I2C and SPI overlays.** Enable the I2C1 overlay for pins 3/5 (`pi-i2c1` on the
   Orange Pi image), then reboot. Check with `i2cdetect -l` (find `5002400.i2c`) and
   `sudo i2cdetect -y <N>` (expect **43**). Then `python3 scripts/power_profile.py` should
   report `"battery_source": "ina219"`. Start the monitor: `sudo scripts/power_daemon.sh`. For
   SPI, build and install `overlays/survival-tft-zero2w.dts` (TFT on SPI1 CS0, round display
   on `/dev/spidev1.1`).
6. **Wire the displays and encoder.** Power off first. Wire them with jumper wires per
   [docs/wiring.md](docs/wiring.md), then test each one:
   - TFT: `cat /sys/class/graphics/fb*/name` shows `fb_ili9341`; `./scripts/test-display.sh`;
     then `sudo scripts/ui-tft.sh` runs the UI on the panel.
   - Encoder: set `"encoder": {"enabled": true}` in `config/default.json`, then run
     `python3 scripts/hw_input.py`.
   - Round display: set `"status_display": {"enabled": true}`, then run
     `python3 scripts/status_display.py`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User Query: "How do I start a fire?"                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ Retrieval (RAG) │  ← Searches local index
         │  chat.py        │     (no internet needed)
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────────────────────┐
         │ Top-K Relevant Chunks          │
         │ • fire-starting.md: §2.1       │
         │ • emergency-medical.md: §5.3   │
         │ • shelter-building.md: §4.2    │
         └────────┬───────────────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ LLM (optional)      │  ← llama.cpp (local)
         │ Synthesize answer   │     or skip for pure RAG
         └─────────┬───────────┘
                   │
                   ▼
         ┌──────────────────────────────────┐
         │ Response + Citations             │
         │ "Use friction method... [1][2]"  │
         │ [1] fire-starting.md             │
         │ [2] shelter-building.md          │
         └──────────────────────────────────┘
```

**Pipeline:**
1. **Ingest** — Documents chunked and indexed (scripts/ingest_booklist.py)
2. **Retrieval** — Query matches chunks via similarity (hash or semantic embeddings)
3. **Generation** — Optional LLM synthesis with citations (llama.cpp)
4. **UI** — Terminal or framebuffer interface (scripts/ui.py)

---

## Content Packs

### Included: Core Survival Pack

8 original reference documents covering:
- Water purification & procurement
- Fire starting techniques
- Emergency shelter building
- First aid basics
- Navigation & orientation
- Food foraging
- Signaling & rescue
- Emergency medical situations

**License:** Public domain (original content based on US Army FM 21-76/FM 3-05.70 principles)

### Adding Your Own Content

1. **Create a manifest** (JSON format):

```json
{
  "documents": [
    {
      "path": "my-guide.md",
      "title": "My Survival Guide",
      "source": "Original work",
      "license": "CC-BY-4.0"
    }
  ]
}
```

2. **Place source files** in `data/sources/`

3. **Run ingest:**

```bash
python3 scripts/ingest_booklist.py \
  --sources data/manifests/my-content.json \
  --sources-directory data/sources \
  --index-path data/index/index.json
```

**Supported formats:** Plain text, Markdown, HTML (more coming soon)

---

## Configuration

Key settings in `config/default.json`:

```json
{
  "index_path": "data/index/index.json",
  "model_path": "models/Qwen3-1.7B-Q4_K_M.gguf",
  "llm_threads": 4,
  "llm_context_tokens": 2048,
  "llm_disable_thinking": "auto",
  "context_k": 6,
  "ina219_i2c_bus": "auto",
  "ina219_address": "0x43",
  "battery_warn_pct": 20,
  "battery_critical_pct": 8
}
```

**Options:**

- `index_path` — Where to store/load the search index. Generated by `setup.sh`, not committed. Paths inside it are stored relative to the repo.
- `model_path` — GGUF model for llama.cpp. **Optional**: if it's empty or the file is missing, chat falls back to retrieval-only answers. Relative paths resolve against the repo root.
- `llm_threads` — 4 (one per Cortex-A53 core). Low-power mode drops it by one.
- `llm_context_tokens` — 2048. Keep it in the 1024–2048 range to stay inside 4 GB. The default prompt (6 chunks of ≤900 chars) is ~1.4k tokens, so 1024 only suits low-power mode (which also cuts `context_k` to 3).
- `llm_disable_thinking` — `"auto"` appends `/no_think` for Qwen3 models so thinking doesn't eat `max_tokens`. `true`/`false` force it on or off.
- `llm_timeout_s` — Per-answer LLM timeout (default 180 s; the A53 is slow).
- `ina219_*` — UPS HAT battery monitor. `ina219_i2c_bus` is `"auto"` (finds the pins-3/5 controller) or a number from `i2cdetect -l`.
- `battery_warn_pct` / `battery_critical_pct` — Low-power thresholds. `battery_shutdown_*` controls the safe shutdown at critical (it needs `battery_shutdown_confirm_reads` consecutive critical, not-charging readings).
- `encoder`, `status_display` — Rotary encoder and round display pins (see [docs/wiring.md](docs/wiring.md)). Both are disabled by default.
- `embedding_model_path` — Path to sentence-transformers model (optional, uses hash fallback if missing)
- `context_k` — Number of chunks to retrieve per query
- `chunk_size` — Characters per chunk during ingest
- `chunk_overlap` — Overlap between chunks to preserve context

**Offline Mode:** Set `model_path` to empty string or use `--offline` flag to skip LLM and return raw retrieval results.

---

## Scripts Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `setup.sh` | First-time setup, dependency check, builds the index | `./scripts/setup.sh [--reindex] [--download-model]` |
| `download_model.sh` | Download a recommended GGUF into the models folder | `./scripts/download_model.sh qwen3-1.7b` |
| `power_daemon.sh` | Battery monitor (INA219), state file, safe shutdown | `sudo ./scripts/power_daemon.sh 30` |
| `power_profile.py` | One-shot battery reading (diagnostics) | `python3 scripts/power_profile.py` |
| `ui-tft.sh` | Run the UI on the 2.8" SPI TFT console | `sudo ./scripts/ui-tft.sh` |
| `hw_input.py` | Rotary encoder test | `python3 scripts/hw_input.py` |
| `status_display.py` | Round display status loop (optional) | `python3 scripts/status_display.py` |
| `ingest_booklist.py` | Build search index from content | `python3 scripts/ingest_booklist.py --sources manifest.json` |
| `chat.py` | Query the knowledge base | `python3 scripts/chat.py "How do I purify water?"` |
| `ui.py` | Interactive terminal/framebuffer UI | `python3 scripts/ui.py` |
| `test-display.sh` | Display hardware test | `./scripts/test-display.sh` |

**Flags:**
- `--offline` — Skip LLM, return retrieval results only
- `--json` — Output as JSON instead of formatted text
- `--debug` — Show full chunk details and scoring

---

## Power & Runtime

**Power path:** USB-C or solar → SeenGreat Pi Zero UPS HAT (B) (built-in charger and MPPT) →
3.7 V LiPo pouch cell → 5 V to the Pi through pogo pins.

**Battery monitoring:** `scripts/power_daemon.sh` reads the HAT's INA219 (I2C 0x43) every
30 s. It estimates LiPo % from voltage (a generic single-cell curve; it reads low under load
and high while charging) and writes `data/runtime/state.json` for the UI, chat and round
display. It switches to reduced/ultra power modes at `battery_warn_pct` /
`battery_critical_pct`, and shuts down safely if the battery stays critical while not
charging. If the INA219 isn't found (pogo contact is a known weak point) everything keeps
running without a battery reading, and the log explains what to check.

**Runtime:** TODO, measure on the real device. Runtime ≈ cell Wh ÷ average draw. For example,
a 3.7 V 2000 mAh cell holds ~7.4 Wh before converter losses. The previous 7Ah LiFePO4
figures in this README don't apply to the pouch-cell build.

**Solar:** connect a 5–24 V panel to the HAT's terminal block. Set the MPPT DIP switch to the
panel's Vmp, with exactly one position ON.

---

## LLM models

Optional. Retrieval-only mode works with no model at all.

| Model | Quant | RAM (approx.) | Role |
|---|---|---|---|
| **Qwen3 1.7B** | Q4_K_M | ~1.9 GB | Default: best answers that fit in 4 GB |
| Gemma 3 1B (it) | Q4_K_M | less | Lighter fallback |
| Qwen3 0.6B | Q4_K_M | least | Speed option |

Not recommended: Llama 3.2 3B, Phi-3 Mini (too heavy for 4 GB on an A53), Gemma 4 E2B (doesn't
fit under llama.cpp on 4 GB).

```bash
./scripts/download_model.sh                 # Qwen3 1.7B Q4_K_M -> models/ (matches default model_path)
./scripts/download_model.sh gemma3-1b --set-config
./scripts/download_model.sh qwen3-0.6b --set-config
```

The download goes into the folder of `model_path` (default `models/`, git-ignored). For Qwen3,
`chat.py` appends `/no_think` to the question and strips any `<think>` block. ⚠️ Recent
llama.cpp builds can start `llama-cli` in interactive conversation mode. If chat hangs until the
timeout, use the one-shot `llama-completion` binary (`"llm_binary": "llama-completion"`), or
add `"-no-cnv"` to `llm_extra_args` on builds that support it.

---

## Development

**Prerequisites:**
- Python 3.10+
- llama.cpp (optional, for LLM mode)
- sentence-transformers (optional, for semantic search)

**Install dev dependencies:**

```bash
source venv/bin/activate
pip install sentence-transformers  # Optional: semantic embeddings
```

**Run tests:**

```bash
# Test ingest
python3 scripts/ingest_booklist.py --sources data/manifests/core-survival.json

# Test retrieval
python3 scripts/chat.py --offline --json "emergency shelter"

# Test display
./scripts/test-display.sh
```

**Compile check:**

```bash
python3 -m py_compile scripts/*.py
```

---

## Contributing

Contributions welcome! Priority areas:

1. **Content packs** — More public domain survival/preparedness content
2. **Hardware adapters** — Support for other SBCs (Raspberry Pi, etc.)
3. **UI improvements** — Better framebuffer rendering, voice interface
4. **Embedding models** — Smaller, faster alternatives
5. **Documentation** — Tutorials, deployment guides

**Guidelines:**
- All content must have clear licensing (prefer public domain or CC-BY)
- Code should work offline-first
- Test on actual hardware when possible
- Keep dependencies minimal

**Submit PRs to:** `main` branch

---

## FAQ

**Q: Does this work without internet?**  
A: Yes. Once ingested, all queries run locally. No network required.

**Q: Do I need an Orange Pi, or can I use a Raspberry Pi?**  
A: Raspberry Pi works fine for development. Production optimizations target Orange Pi Zero 2W for cost/power reasons.

**Q: Can I add my own survival manuals?**  
A: Yes! Just create a manifest pointing to your files and run ingest. See "Content Packs" above.

**Q: What LLM should I use?**  
A: On a 4GB Cortex-A53 board, use **Qwen3 1.7B Q4_K_M** (default, about 1.9GB RAM). **Gemma 3 1B** is a lighter fallback, and **Qwen3 0.6B** is the speed option. Llama 3.2 3B / Phi-3 Mini are too heavy for this board, and Gemma 4 E2B doesn't fit under llama.cpp on 4GB. See [LLM models](#llm-models).

**Q: Which pins / bus numbers do I use?**  
A: See [docs/wiring.md](docs/wiring.md). The Zero 2W's I2C and SPI bus numbers differ from a Raspberry Pi's.

**Q: What if I don't have llama.cpp installed?**  
A: Use `--offline` mode. You'll get direct retrieval results with citations, no synthesis.

**Q: Is this medical/legal advice?**  
A: No. This is reference material only. Verify with professionals for critical decisions.

---

## License

MIT License — see [LICENSE](LICENSE) file for details.

Copyright © 2026 Stratus Labs, LLC

---

## Acknowledgments

Content based on principles from:
- US Army FM 21-76 (Survival Manual)
- US Army FM 3-05.70 (Survival, Evasion, and Recovery)

Built with:
- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [sentence-transformers](https://www.sbert.net/) (optional)

---

**Status:** ✅ MVP Complete — Ready for field testing

**Version:** 1.0.0

**Last Updated:** November 2026
