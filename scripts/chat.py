#!/usr/bin/env python3
"""CLI chat wrapper for offline RAG + local LLM.

Phase 2 hardening:
- citation-first output
- confidence estimate (requires retrieval hit quality)
- low-power mode adaptation
- structured audit logging
- safe fallback path when model/tooling unavailable
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ingest_booklist import VectorModel, build_model, load_config
from power_profile import assess


UNSAFE_LICENSES = {
    "all-rights-reserved",
    "copyrighted",
    "proprietary",
    "restricted",
}


def read_index(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Candidate:
    chunk: Dict[str, Any]
    score: float


def top_k_chunks(query_vec: Sequence[float], chunks: List[Dict[str, Any]], model: VectorModel, k: int = 6) -> List[Candidate]:
    scored: List[Candidate] = []
    for row in chunks:
        emb = row.get("embedding", [])
        sim = model.similarity(query_vec, emb)
        scored.append(Candidate(chunk=row, score=float(sim)))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:k]


def allowed_sources(context: List[Candidate], cfg: Dict[str, Any]) -> List[Candidate]:
    # Hard safety rail: skip chunks with blocked license metadata unless explicitly overridden.
    allow_unknown = bool(cfg.get("allow_unknown_licenses", False))
    allowed = []
    for c in context:
        license_value = str((c.chunk.get("metadata") or {}).get("license", "unknown")).lower()
        is_blocked = any(b in license_value for b in UNSAFE_LICENSES)
        if is_blocked:
            print(f"[WARN] Skipping blocked license chunk: {license_value}")
            continue
        if license_value == "unknown" and not allow_unknown:
            print(f"[WARN] Skipping unknown-license chunk (document: {c.chunk.get('chunk_id', 'n/a')})")
            continue
        allowed.append(c)
    return allowed


def confidence_score(context: List[Candidate]) -> float:
    if not context:
        return 0.0
    top = context[0].score if context else 0.0
    average = sum(c.score for c in context) / len(context)
    # Hash-embedding fallback tends to yield low absolute cosines.
    # Apply a gentle scaling + clamp so "somewhat relevant" passages don't all read as 0.1 confidence.
    raw = (top * 0.8 + average * 0.2)
    scaled = min(1.0, max(0.0, raw * 3.5))
    return scaled


def low_power_adjust(cfg: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    profile = dict(cfg)

    if not force:
        return profile

    # Reduce load when low-power is requested or battery is low.
    profile["context_k"] = min(int(profile.get("context_k", 6)), 3)
    profile["max_tokens"] = min(int(profile.get("max_tokens", 512)), 192)
    profile["llm_threads"] = max(1, int(profile.get("llm_threads", 2)) - 1)
    profile["llm_context_tokens"] = int(profile.get("llm_context_tokens", 1024))
    profile["llm_context_tokens"] = max(640, int(profile["llm_context_tokens"]) // 2)
    return profile


def build_prompt(query: str, context: List[Candidate], max_tokens: int, temperature: float) -> str:
    lines: List[str] = []
    lines.append("You are a practical, concise survival assistant for offline field use.")
    lines.append("Use only the provided local context. Never invent details not present in context.")
    lines.append("If confidence is low, explicitly say it is low and suggest a conservative checklist instead.")
    lines.append("Always cite statements using [1], [2], etc matching the provided Context order.")
    lines.append(
        "Prefer safety-first recommendations and include any caveats. "
        "If the context is insufficient for a potentially unsafe action, advise against it."
    )
    lines.append(f"Safety posture: temperature={temperature}, max_tokens={max_tokens}.")
    lines.append("")
    lines.append("Context:")

    for i, item in enumerate(context, start=1):
        meta = item.chunk.get("metadata", {})
        lines.append(
            f"[{i}] Title: {meta.get('title', 'unknown')} | Source: {meta.get('source', 'unknown')} | "
            f"License: {meta.get('license', 'unknown')} | Url: {meta.get('source_url', '')}"
        )
        snippet = item.chunk.get("text", "")
        lines.append(snippet[:1200])
        lines.append("")

    lines.append(f"User question: {query}")
    lines.append("Respond in short steps + include citations [1], [2] where applicable.")

    return "\n".join(lines)


def invoke_llm(cfg: Dict[str, Any], prompt: str) -> str:
    binary = str(cfg.get("llm_binary", "llama-cli"))
    model_path = str(cfg.get("model_path", "")).strip()
    max_tokens = int(cfg.get("max_tokens", 512))
    temperature = float(cfg.get("temperature", 0.2))
    threads = str(int(cfg.get("llm_threads", 2)))

    if not shutil.which(binary):
        return "(LOCAL LLM NOT FOUND) Configure llm_binary and install it before query mode."
    if not model_path:
        return "(MODEL PATH NOT CONFIGURED) Set model_path in config/default.json."

    # Skip hard-fail if model absent on disk.
    if not Path(model_path).exists():
        return f"(MODEL NOT FOUND) Missing {model_path}. Set up offline model file first."

    # A soft compatibility matrix for common runners.
    if binary == "llama-cli":
        cmd = [binary, "-m", model_path, "-p", prompt, "--temp", str(temperature), "-n", str(max_tokens)]
    elif binary == "llama.cpp":
        cmd = [binary, "-m", model_path, "-p", prompt, "-n", str(max_tokens), "-c", str(int(cfg.get("llm_context_tokens", 2048))), "--threads", threads]
    else:
        cmd = [binary, "-m", model_path, "-p", prompt, "--temp", str(temperature), "--tokens", str(max_tokens)]

    # Respect optional extra flags from config.
    extra_flags = cfg.get("llm_extra_args")
    if isinstance(extra_flags, list):
        cmd.extend([str(x) for x in extra_flags])

    try:
        proc = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return f"(LLM ERROR code={proc.returncode})\n{proc.stdout or ''}"
        return proc.stdout.strip() or "No output from model."
    except subprocess.TimeoutExpired:
        return "(LLM TIMEOUT) Response timed out. Try again with fewer tokens/context."
    except Exception as exc:
        return f"(LLM FAILED) {exc}"


def fallback_answer(query: str, context: List[Candidate], conf: float) -> str:
    if not context:
        return (
            "I don't have enough trusted local sources for this question yet. "
            "Add more manuals to the source index and ask again."
        )

    snippet_lines = ["\nTrusted snippets:\n"]
    for i, item in enumerate(context, start=1):
        chunk = item.chunk
        snippet_lines.append(f"[{i}] {chunk.get('text', '')[:380]}")

    confidence_msg = "high" if conf >= 0.7 else "moderate" if conf >= 0.45 else "low"
    return (
        f"Model offline path unavailable."
        f" I can still provide retrieval-only guidance from local sources at {confidence_msg} confidence:\n"
        + "\n".join(snippet_lines)
        + "\n\nThis should be verified before acting."
    )


def format_citations(context: List[Candidate]) -> str:
    rows = []
    for i, candidate in enumerate(context, start=1):
        m = candidate.chunk.get("metadata", {})
        source = m.get("source", "unknown")
        title = m.get("title", "")
        url = m.get("source_url", "")
        path = m.get("path", "")
        score = candidate.score
        rows.append(f"[{i}] score={score:.3f} title='{title}' source='{source}' url='{url or path}'")
    return "\n".join(rows)


def append_audit(log_path: Path, payload: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def parse_battery_pct(cfg: Dict[str, Any]) -> int | None:
    if not bool(cfg.get("battery_monitor_enabled", False)):
        return None

    state = assess(cfg)
    return state.percent


def current_mode(cfg: Dict[str, Any]) -> str:
    if not bool(cfg.get("battery_monitor_enabled", False)):
        return "normal"

    return assess(cfg).recommended_mode



def main() -> int:
    parser = argparse.ArgumentParser(description="Offline RAG chat")
    parser.add_argument("query", nargs="?", help="Question to ask")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config" / "default.json"))
    parser.add_argument("--k", type=int, default=None, help="Override context_k")
    parser.add_argument("--index", default=None, help="Override index path")
    parser.add_argument("--offline", action="store_true", help="Force retrieval-only output")
    parser.add_argument("--low-power", action="store_true", help="Use low-power profile")
    parser.add_argument("--json", action="store_true", help="Emit JSON payload for automation")
    parser.add_argument("--interactive", action="store_true", help="Stay in interactive mode")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    index_path = Path(args.index or cfg.get("index_path", "data/index/index.json"))
    if not index_path.exists():
        print(f"Index not found at {index_path}. Run ingest_booklist.py first.")
        return 2

    model = build_model(cfg)
    battery_mode = current_mode(cfg)
    force_low_power = bool(args.low_power) or battery_mode in {"reduced", "ultra"}
    profile = low_power_adjust(cfg, force=bool(force_low_power))
    profile["power_mode"] = battery_mode

    index = read_index(index_path)
    chunks = index.get("chunks", [])
    if not chunks:
        print("Index has no chunks.")
        return 2

    # interactive mode with no positional query
    def process_query(query: str) -> Dict[str, Any]:
        if not query:
            return {
                "answer": "No query provided.",
                "citations": [],
                "confidence": 0.0,
                "low_power": bool(force_low_power),
                "retrieved": 0,
                "source": "error",
            }

        query_vec = model.embed(query)
        context = top_k_chunks(query_vec, chunks, model=model, k=int(args.k or profile.get("context_k", 6)))

        context = [c for c in context if c.score > 0]
        context = allowed_sources(context, profile)

        conf = confidence_score(context)

        selected = context[: int(profile.get("context_k", 6))]

        context_text = "\n\n".join([f"[{i+1}] {c.chunk.get('text','')}" for i, c in enumerate(selected)])
        prompt = build_prompt(query, selected, int(profile.get("max_tokens", 512)), float(profile.get("temperature", 0.2)))

        if args.offline:
            answer = fallback_answer(query, selected, conf)
        else:
            answer = invoke_llm(profile, prompt)
            if answer.startswith("("):
                # If local model invocation failed, keep safe fallback mode.
                answer = fallback_answer(query, selected, conf) + "\n\n" + answer

        payload = {
            "answer": answer,
            "citations": selected,
            "context_block": context_text,
            "query": query,
            "confidence": conf,
            "low_power": bool(force_low_power),
            "retrieved": len(selected),
            "top_score": selected[0].score if selected else 0.0,
            "source": "local_llm" if not args.offline and not answer.startswith("(LOCAL LLM NOT FOUND)") else "retrieval_only",
        }

        if conf < float(profile.get("min_confidence", 0.28)):
            prefix = (
                "Low confidence from local sources. "
                "Please cross-check with alternate docs before attempting risky actions.\n"
            )
            payload["answer"] = prefix + payload["answer"]

        battery_pct = parse_battery_pct(profile)
        if battery_pct is not None:
            payload["battery_pct"] = battery_pct
            if battery_pct <= int(profile.get("battery_warn_pct", 20)):
                payload["power_warning"] = "battery_low"
            if battery_pct <= int(profile.get("battery_critical_pct", 8)):
                payload["power_warning"] = "battery_critical"
        payload["power_mode"] = profile.get("power_mode", "normal")

        append_audit(Path("logs/chat-audit.jsonl"), {
            "ts": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "confidence": conf,
            "top_score": payload["top_score"],
            "retrieved": len(selected),
            "low_power": bool(force_low_power),
            "battery_pct": battery_pct,
            "source": payload["source"],
        })

        if args.json:
            out = {
                "answer": payload["answer"],
                "citations": [c.chunk.get("metadata", {}) for c in selected],
                "confidence": conf,
                "low_power": bool(force_low_power),
                "retrieved": len(selected),
                "top_score": payload["top_score"],
                "battery_pct": battery_pct,
                "power_warning": payload.get("power_warning"),
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print("\n=== ANSWER ===")
            print(payload["answer"])
            print("\n=== METRICS ===")
            print(f"confidence={conf:.3f} top_score={payload['top_score']:.3f} retrieved={payload['retrieved']}")
            if battery_pct is not None:
                print(f"battery_pct={battery_pct}")
            print("\n=== CITATIONS ===")
            print(format_citations(selected))

        return payload

    if args.interactive:
        while True:
            try:
                line = input("> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nbye")
                break
            if not line:
                continue
            if line.lower() in {"exit", "quit", "/q"}:
                break
            process_query(line)
        return 0

    if not args.query:
        parser.error("Query required. Use --interactive or pass query. Example: python3 chat.py \"What is hypothermia first aid?\"")

    process_query(args.query)
    return 0


if __name__ == "__main__":
    sys.exit(main())
