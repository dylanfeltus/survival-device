# Survival AI Device

An offline-first survival knowledge system for Orange Pi Zero 2W. Ask questions about water purification, fire starting, first aid, navigation, and more — all without internet connectivity.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/survival-device.git
cd survival-device

# 2. Run setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Ingest survival content
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

**Target Platform:** Orange Pi Zero 2W 4GB

### Bill of Materials

| Component | Spec | Link |
|-----------|------|------|
| SBC | Orange Pi Zero 2W 4GB | [OrangePi.org](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/details/Orange-Pi-Zero-2W.html) |
| Storage | 32GB+ microSD (Class 10) | [Amazon](https://amazon.com/s?k=microsd+32gb) |
| Display | 480x320 SPI LCD or HDMI | [Waveshare 3.5"](https://www.waveshare.com/3.5inch-rpi-lcd-a.htm) |
| Power | 5V UPS HAT + 7Ah battery | [Waveshare UPS HAT](https://www.waveshare.com/wiki/UPS_HAT_(D)) |
| Solar (opt) | 20W panel + MPPT controller | [Voltaic](https://voltaicsystems.com/) |
| Input | Rotary encoder + buttons | [Adafruit](https://www.adafruit.com/product/377) |

**Desktop Development:** Runs on any Linux/macOS/Windows system with Python 3.10+

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
  "model_path": "/path/to/model.gguf",
  "embedding_model_path": "/path/to/embeddings",
  "context_k": 3,
  "chunk_size": 512,
  "chunk_overlap": 64
}
```

**Options:**

- `index_path` — Where to store/load the search index
- `model_path` — Path to GGUF model file for llama.cpp (optional)
- `embedding_model_path` — Path to sentence-transformers model (optional, uses hash fallback if missing)
- `context_k` — Number of chunks to retrieve per query
- `chunk_size` — Characters per chunk during ingest
- `chunk_overlap` — Overlap between chunks to preserve context

**Offline Mode:** Set `model_path` to empty string or use `--offline` flag to skip LLM and return raw retrieval results.

---

## Scripts Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `setup.sh` | First-time setup and dependency check | `./scripts/setup.sh` |
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

**Typical Power Draw:**
- Idle (display on): ~3.5W
- Active query: ~6.5W peak

**Battery Runtime (7Ah LiFePO4):**
- ~19 hours idle
- ~16 hours mixed use

**Solar Charging:**
- 20W panel, 4h sun/day = ~56Wh/day
- Sufficient for intermittent use with overnight reserve

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
A: Any GGUF model compatible with llama.cpp. Recommend Llama 3.2 3B or Phi-3 Mini for 4GB RAM.

**Q: What if I don't have llama.cpp installed?**  
A: Use `--offline` mode. You'll get direct retrieval results with citations, no synthesis.

**Q: Is this medical/legal advice?**  
A: No. This is reference material only. Verify with professionals for critical decisions.

---

## License

MIT License — see [LICENSE](LICENSE) file for details.

Copyright © 2024 Stratus Labs, LLC

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

**Last Updated:** March 2024
