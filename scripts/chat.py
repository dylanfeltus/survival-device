#!/usr/bin/env python3
"""CLI chat wrapper for offline RAG + local LLM.

Behavior:
1) Load index JSON built by ingest_booklist.py
2) Embed query
3) Retrieve top-k chunks by cosine similarity
4) Pass query + retrieved context to local LLM binary (if present)
5) Print answer plus source citations
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ingest_booklist import VectorModel, build_model, load_config, _dot, _norm


def read_index(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def top_k_chunks(query_vec: Sequence[float], chunks: List[Dict[str, Any]], model: VectorModel, k: int = 6) -> List[Dict[str, Any]]:
    scored = []
    for row in chunks:
        emb = row.get("embedding", [])
        sim = model.similarity(query_vec, emb)
        scored.append((sim, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [r for _, r in scored[:k]]


def build_prompt(query: str, context: List[Dict[str, Any]], max_tokens: int, temperature: float) -> str:
    lines = []
    lines.append("You are a practical survival assistant for offline field use.")
    lines.append("Use only provided sources below to answer. If uncertain, state uncertainty clearly.")
    lines.append("Always include citations using format [S1], [S2], etc.")
    lines.append("Never invent claims not grounded in context.")
    lines.append("")
    lines.append("Context:")

    for i, item in enumerate(context, start=1):
        meta = item.get("metadata", {})
        lines.append(f"[{i}] Title: {meta.get('title','unknown')} | Source: {meta.get('source','unknown')} | License: {meta.get('license','unknown')} | Url: {meta.get('source_url','')}")
        lines.append(item.get("text", ""))
        lines.append("")

    lines.append(f"User question: {query}")
    lines.append("Respond with a short operational answer and include citation markers like [1], [2], ...")

    return "\n".join(lines)


def invoke_llm(cfg: Dict[str, Any], prompt: str) -> str:
    binary = cfg.get("llm_binary", "llama-cli")
    model_path = cfg.get("model_path", "")
    max_tokens = int(cfg.get("max_tokens", 512))
    temperature = float(cfg.get("temperature", 0.2))

    # Minimal command matrix for common offline binaries
    cmds = {
        "llama-cli": [binary, "-m", model_path, "-p", prompt, "--temp", str(temperature), "-n", str(max_tokens)],
        "llama.cpp": [binary, "-m", model_path, "-p", prompt, "-n", str(max_tokens), "-c", str(2048)],
        "llama-run": [binary, model_path, prompt],
    }

    # Prefer explicit llm_binary match, fallback to llama-cli style.
    command = cmds.get(binary) or [binary, "--model", model_path, "--prompt", prompt, "--temp", str(temperature), "--tokens", str(max_tokens)]

    # Skip invoking when binary missing or model not provisioned.
    if not shutil_which(binary):
        return "(LOCAL LLM NOT FOUND) " \
            "Install and configure llm_binary in config/default.json, then rerun.\n" \
            + fallback_answer(prompt, "")

    if not model_path or not Path(model_path).exists():
        return "(MODEL NOT FOUND) Configure model_path in config/default.json.\n" + fallback_answer(prompt, "")

    try:
        proc = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return f"(LLM ERROR code={proc.returncode})\n{proc.stdout or ''}"
        return proc.stdout.strip() or fallback_answer(prompt, "")
    except Exception as exc:
        return f"(LLM INVOCATION FAILED) {exc}"


def fallback_answer(prompt: str, context_block: str) -> str:
    return f"Unable to run LLM binary. Context-only fallback for question: {prompt}\n{context_block}"


def shutil_which(binary: str) -> str:
    from shutil import which

    return which(binary)


def format_citations(context: List[Dict[str, Any]]) -> str:
    rows = []
    for i, chunk in enumerate(context, start=1):
        m = chunk.get("metadata", {})
        source = m.get("source", "unknown")
        title = m.get("title", "")
        url = m.get("source_url", "")
        path = m.get("path", "")
        rows.append(f"[{i}] {title} | {source} | {url or path}")
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline RAG chat")
    parser.add_argument("query", nargs="?", help="Question to ask")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config" / "default.json"))
    parser.add_argument("--k", type=int, default=None, help="Override context_k")
    parser.add_argument("--index", default=None, help="Override index path")
    parser.add_argument("--offline", action="store_true", help="Force text-only retrieval output")
    args = parser.parse_args()

    if not args.query:
        parser.error("Query required. Example: python3 chat.py \"What is hypothermia first aid?\"")

    cfg = load_config(Path(args.config))
    index_path = Path(args.index or cfg.get("index_path", "data/index/index.json"))
    if not index_path.exists():
        print(f"Index not found at {index_path}. Run ingest_booklist.py first.")
        return 2

    index = read_index(index_path)
    chunks = index.get("chunks", [])
    if not chunks:
        print("Index has no chunks.")
        return 2

    k = int(args.k or cfg.get("context_k", 6))
    model = build_model(cfg)

    query_vec = model.embed(args.query)
    context = top_k_chunks(query_vec, chunks, model=model, k=k)

    context_snippets = "\n\n".join([f"[{i+1}] {c.get('text','')}" for i, c in enumerate(context)])
    prompt = build_prompt(args.query, context, int(cfg.get("max_tokens", 512)), float(cfg.get("temperature", 0.2)))

    if args.offline:
        print("[OFFLINE MODE] Retrieved context (no LLM call):")
        print(context_snippets)
        print("\nCITATIONS:")
        print(format_citations(context))
        return 0

    answer = invoke_llm(cfg, prompt)
    print("\n=== ANSWER ===")
    print(answer)
    print("\n=== CITATIONS ===")
    print(format_citations(context))
    return 0


if __name__ == "__main__":
    sys.exit(main())
