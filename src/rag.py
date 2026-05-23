from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np

from src.notes import (
    MAX_FILE_BYTES,
    NoteMatch,
    _iter_candidate_files,
    _make_snippet,
    _read_searchable_text,
    terms_from_text,
)

INDEX_DIR = Path.home() / ".cadbury" / "rag"
INDEX_META_PATH = INDEX_DIR / "meta.json"
INDEX_CHUNKS_PATH = INDEX_DIR / "chunks.json"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
MAX_CHUNKS_PER_FILE = 80
TOP_K = 5
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"

_MODEL = None


class EmbeddingModelError(RuntimeError):
    """Embedding model could not be loaded (missing cache or network failure)."""


@dataclass(frozen=True)
class ChunkRecord:
    path: str
    mtime: float
    chunk_index: int
    text: str
    embedding: list[float]


def _load_model(model_name: str, *, allow_download: bool = True):
    """Load the sentence-transformers model, preferring the local HF cache."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    from sentence_transformers import SentenceTransformer

    strategies: list[dict[str, bool]] = [{"local_files_only": True}]
    if allow_download:
        strategies.append({"local_files_only": False})

    last_exc: Exception | None = None
    transient = (
        httpx.RemoteProtocolError,
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.TimeoutException,
    )

    for kwargs in strategies:
        attempts = 3 if not kwargs["local_files_only"] else 1
        for attempt in range(attempts):
            try:
                _MODEL = SentenceTransformer(model_name, **kwargs)
                return _MODEL
            except Exception as exc:
                last_exc = exc
                if kwargs["local_files_only"]:
                    break
                if isinstance(exc, transient) and attempt < attempts - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break

    hint = (
        "Model is cached locally but could not be opened."
        if not allow_download
        else "Run once while online: cadbury index (downloads the embedding model)."
    )
    raise EmbeddingModelError(
        f"Could not load embedding model '{model_name}'. {hint} "
        f"Details: {last_exc}"
    ) from last_exc


def _chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text) and len(chunks) < MAX_CHUNKS_PER_FILE:
        end = min(len(text), start + CHUNK_SIZE)
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return [c for c in chunks if c]


def index_exists() -> bool:
    return INDEX_META_PATH.exists() and INDEX_CHUNKS_PATH.exists()


def build_index(allowed_paths: list[Path], model_name: str = DEFAULT_EMBED_MODEL) -> str:
    try:
        model = _load_model(model_name, allow_download=True)
    except EmbeddingModelError as exc:
        return str(exc)
    records: list[ChunkRecord] = []
    files_seen = 0

    for file_path in _iter_candidate_files(allowed_paths, None):
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                continue
            mtime = file_path.stat().st_mtime
        except OSError:
            continue

        text = _read_searchable_text(file_path)
        if not text or len(text.strip()) < 20:
            continue

        files_seen += 1
        chunks = _chunk_text(text)
        if not chunks:
            continue

        vectors = model.encode(chunks, show_progress_bar=False)
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            records.append(
                ChunkRecord(
                    path=str(file_path.resolve()),
                    mtime=mtime,
                    chunk_index=idx,
                    text=chunk,
                    embedding=vector.tolist(),
                )
            )

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "model": model_name,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "files_indexed": files_seen,
        "chunks": len(records),
        "allowed_roots": [str(p) for p in allowed_paths],
    }
    INDEX_META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    INDEX_CHUNKS_PATH.write_text(
        json.dumps([record.__dict__ for record in records]),
        encoding="utf-8",
    )
    return (
        f"Indexed {files_seen} files into {len(records)} chunks "
        f"using {model_name}."
    )


def _load_chunks() -> list[ChunkRecord]:
    raw = json.loads(INDEX_CHUNKS_PATH.read_text(encoding="utf-8"))
    return [ChunkRecord(**item) for item in raw]


def semantic_search(
    query: str,
    *,
    restrict_files: list[Path] | None = None,
    top_k: int = TOP_K,
) -> list[NoteMatch]:
    if not index_exists() or not query.strip():
        return []

    meta = json.loads(INDEX_META_PATH.read_text(encoding="utf-8"))
    try:
        model = _load_model(
            meta.get("model", DEFAULT_EMBED_MODEL),
            allow_download=False,
        )
    except EmbeddingModelError:
        return []
    chunks = _load_chunks()

    if restrict_files:
        allowed = {str(path.resolve()) for path in restrict_files}
        chunks = [c for c in chunks if c.path in allowed]

    if not chunks:
        return []

    query_vec = model.encode([query], show_progress_bar=False)[0]
    matrix = np.array([c.embedding for c in chunks], dtype=np.float32)
    q = np.array(query_vec, dtype=np.float32)
    denom = (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q)) + 1e-8
    scores = (matrix @ q) / denom

    ranked = np.argsort(scores)[::-1][:top_k]
    query_terms = terms_from_text(query)
    matches: list[NoteMatch] = []
    seen_paths: set[str] = set()

    for idx in ranked:
        chunk = chunks[int(idx)]
        score = int(float(scores[int(idx)]) * 1000)
        if score <= 0:
            continue
        if chunk.path in seen_paths:
            continue
        seen_paths.add(chunk.path)
        matches.append(
            NoteMatch(
                path=Path(chunk.path),
                score=score,
                snippet=_make_snippet(chunk.text, query_terms or [query.lower()], window=400),
            )
        )
    return matches
