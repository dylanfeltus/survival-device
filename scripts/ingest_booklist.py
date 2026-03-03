#!/usr/bin/env python3
"""
Offline ingestion script for Survival AI.

Inputs:
- JSON: list of source descriptors, or object with "documents" key.
- CSV: header row supported.

Required fields per source document:
- path (required): local file path to a UTF-8 text document.
Optional:
- title, source, license, license_url, source_url, language, section

Output:
- JSON index at --index-path (default from config/default.json)
- Deterministic chunk IDs and metadata for citation
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import sys


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_json_sources(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("documents"), list):
        items = payload["documents"]
    else:
        raise ValueError("JSON input must be a list or object with 'documents' list")

    if not isinstance(items, list):
        raise ValueError("Source list malformed")

    return items


def parse_csv_sources(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("path"):
                continue
            items.append({k: v for k, v in row.items() if v not in (None, "")})
    return items


@dataclass
class VectorModel:
    dim: int
    model: Any = None
    use_numpy: bool = False

    def _text_tokens(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9']+", text.lower())

    def embed(self, text: str) -> List[float]:
        if self.model is not None:
            try:
                vec = self.model.encode([text], convert_to_numpy=True)[0]
                # normalize
                return _normalize(vec).tolist()
            except Exception:
                pass

        # Deterministic fallback: hashed token counts with signed projection.
        vec = [0.0] * self.dim
        for token in self._text_tokens(text):
            h = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 1) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def similarity(self, a: Sequence[float], b: Sequence[float]) -> float:
        if self.use_numpy:
            import numpy as np

            av = np.array(a, dtype="float32")
            bv = np.array(b, dtype="float32")
            denom = (np.linalg.norm(av) * np.linalg.norm(bv))
            return float(av @ bv / denom) if denom else 0.0

        return _dot(a, b)


def build_model(cfg: Dict[str, Any]) -> VectorModel:
    dim = int(cfg.get("embedding_dim", 384))

    # Optional dependency for better quality embeddings
    model_name_or_path = cfg.get("embedding_model_path") or ""
    if model_name_or_path:
        try:
            from sentence_transformers import SentenceTransformer

            m = SentenceTransformer(model_name_or_path)
            return VectorModel(dim=dim, model=m, use_numpy=True)
        except Exception as exc:
            print(f"[WARN] Could not load embedding model ({model_name_or_path}). Falling back to hash embeddings: {exc}")

    # Optional: lightweight dependency in case present
    try:
        import numpy  # noqa: F401

        return VectorModel(dim=dim, model=None, use_numpy=True)
    except Exception:
        return VectorModel(dim=dim, model=None, use_numpy=False)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    chunks = []
    if not text:
        return chunks

    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    i = 0
    while i < len(cleaned):
        end = min(len(cleaned), i + chunk_size)
        chunk = cleaned[i:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(cleaned):
            break
        i = max(0, end - overlap)
    return chunks


def file_to_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown", ".json"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix} ({path})")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _norm(a: Sequence[float]) -> float:
    return math.sqrt(_dot(a, a))


def _normalize(vec: Sequence[float]):
    if not hasattr(vec, "__iter__"):
        return vec
    n = math.sqrt(sum(float(v) * float(v) for v in vec))
    if n == 0:
        return vec
    return vec / n


def build_index(
    sources: List[Dict[str, Any]],
    sources_root: Path,
    index_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> Dict[str, Any]:
    cfg = load_config(Path(__file__).resolve().parent.parent / "config" / "default.json")
    model = build_model(cfg)

    chunks_out: List[Dict[str, Any]] = []
    docs_out: List[Dict[str, Any]] = []
    chunk_id = 0

    for doc in sources:
        src_path = Path(doc.get("path", "")).expanduser()
        if not src_path.is_absolute():
            src_path = (sources_root / src_path).resolve()

        if not src_path.exists():
            print(f"[WARN] Missing source path: {src_path}")
            continue

        text = file_to_text(src_path)
        if not text.strip():
            print(f"[WARN] Empty file, skipped: {src_path}")
            continue

        doc_id = hashlib.md5(str(src_path).encode("utf-8")).hexdigest()
        doc_record = {
            "doc_id": doc_id,
            "path": str(src_path),
            "title": doc.get("title", src_path.stem),
            "source": doc.get("source", "unknown"),
            "license": doc.get("license", "unknown"),
            "license_url": doc.get("license_url", ""),
            "source_url": doc.get("source_url", ""),
            "language": doc.get("language", "en"),
            "domain": doc.get("domain", "other"),
            "sha256": sha256_file(src_path),
            "ingested_at": now_utc(),
        }
        docs_out.append(doc_record)

        parts = chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        if not parts:
            print(f"[WARN] No chunks from: {src_path}")
            continue

        for i, chunk_text_value in enumerate(parts):
            emb = model.embed(chunk_text_value)
            chunks_out.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "text": chunk_text_value,
                    "embedding": emb,
                    "metadata": {
                        "title": doc_record["title"],
                        "source": doc_record["source"],
                        "license": doc_record["license"],
                        "source_url": doc_record["source_url"],
                        "path": str(src_path),
                    },
                }
            )
            chunk_id += 1

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index = {
        "created_at": now_utc(),
        "version": "v1",
        "embedding_dim": model.dim,
        "documents": docs_out,
        "chunks": chunks_out,
    }
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return {
        "document_count": len(docs_out),
        "chunk_count": len(chunks_out),
        "index_path": str(index_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local chunk/embedding index")
    parser.add_argument("--sources", required=True, help="Path to JSON/CSV list of source documents")
    parser.add_argument("--index-path", default="", help="Output index path. Defaults from config/default.json")
    parser.add_argument("--sources-directory", default="", help="Directory for relative source paths")
    parser.add_argument("--chunk-size", type=int, default=None, help="Chunk size in chars")
    parser.add_argument("--chunk-overlap", type=int, default=None, help="Chunk overlap in chars")
    args = parser.parse_args()

    base_cfg = load_config(Path(__file__).resolve().parent.parent / "config" / "default.json")
    sources_dir = (
        Path(args.sources_directory)
        if args.sources_directory
        else Path(base_cfg.get("sources_directory", "data/sources"))
    )

    if args.index_path:
        index_path = Path(args.index_path)
    else:
        index_path = Path(base_cfg.get("index_path", "data/index/index.json"))

    chunk_size = args.chunk_size if args.chunk_size is not None else int(base_cfg.get("chunk_size_chars", 900))
    chunk_overlap = args.chunk_overlap if args.chunk_overlap is not None else int(base_cfg.get("chunk_overlap_chars", 120))

    src_path = Path(args.sources)
    if not src_path.exists():
        print(f"Source file not found: {src_path}")
        return 2

    if src_path.suffix.lower() == ".csv":
        sources = parse_csv_sources(src_path)
    else:
        sources = parse_json_sources(src_path)

    if not sources:
        print("No source docs found in manifest.")
        return 2

    print(f"Loaded {len(sources)} source rows")
    summary = build_index(
        sources=sources,
        sources_root=sources_dir,
        index_path=index_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
