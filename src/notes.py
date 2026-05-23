from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from pypdf import PdfReader

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".xml",
    ".log",
}
PDF_SUFFIX = ".pdf"
DOCX_SUFFIX = ".docx"
MAX_RESULTS = 5
MAX_FILE_BYTES = 5_000_000
MAX_CONTEXT_CHARS = 3500

# Skip noisy trees when allowlisting broad folders (e.g. a whole projects directory).
SKIP_DIR_NAMES = frozenset({
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "site-packages",
    ".cadbury",
    "dist",
    "build",
    ".egg-info",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".cursor",
    ".idea",
    ".vscode",
    "rag",
})

# Suffixes worth indexing/searching (excludes .js bundles under venvs, etc.).
INDEXABLE_SUFFIXES = (TEXT_SUFFIXES - {".js", ".html", ".css"}) | {PDF_SUFFIX, DOCX_SUFFIX}


@dataclass(frozen=True)
class NoteMatch:
    path: Path
    score: int
    snippet: str


def terms_from_text(text: str, *, min_len: int = 3) -> list[str]:
    """Extract searchable terms from user text (no domain-specific defaults)."""
    raw_terms = re.findall(r"[a-zA-Z0-9_.-]+", text.lower())
    stop = {
        "what", "does", "contain", "about", "with", "from", "this", "that",
        "your", "have", "tell", "summarize", "summary", "contents", "content",
        "file", "document", "please", "can", "you", "the", "and", "for",
    }
    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        if len(term) < min_len or term in stop:
            continue
        if term not in seen:
            seen.add(term)
            terms.append(term)
    return terms


def _score_text(text: str, query: str) -> int:
    return text.lower().count(query.lower())


def _make_snippet(text: str, query_terms: list[str], window: int = 120) -> str:
    lower = text.lower()
    idx = -1
    for term in query_terms:
        idx = lower.find(term)
        if idx != -1:
            break
    if idx == -1:
        return text[:window].replace("\n", " ").strip()
    anchor_len = len(query_terms[0]) if query_terms else 0
    start = max(0, idx - window // 2)
    end = min(len(text), idx + anchor_len + window // 2)
    return text[start:end].replace("\n", " ").strip()


def _read_pdf(file_path: Path) -> str:
    try:
        reader = PdfReader(str(file_path))
    except Exception:
        return ""
    pages: list[str] = []
    for page in reader.pages[:20]:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages).strip()


def _read_docx(file_path: Path) -> str:
    try:
        document = Document(str(file_path))
    except Exception:
        return ""
    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


def _read_searchable_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    try:
        if suffix in TEXT_SUFFIXES:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        if suffix == PDF_SUFFIX:
            return _read_pdf(file_path)
        if suffix == DOCX_SUFFIX:
            return _read_docx(file_path)
    except OSError:
        return ""
    return ""


def _iter_candidate_files(
    allowed_paths: list[Path],
    restrict_files: list[Path] | None,
) -> list[Path]:
    if restrict_files:
        return [path.resolve() for path in restrict_files if path.exists() and path.is_file()]

    candidates: list[Path] = []
    for root in allowed_paths:
        if not root.exists():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in file_path.parts):
                continue
            if file_path.suffix.lower() not in INDEXABLE_SUFFIXES:
                continue
            candidates.append(file_path)
    return candidates


def get_document_excerpt(
    file_path: Path,
    query_terms: list[str],
    max_chars: int = MAX_CONTEXT_CHARS,
) -> str:
    text = _read_searchable_text(file_path)
    if not text:
        return ""
    if len(text) <= max_chars:
        return text

    lower = text.lower()
    for term in query_terms:
        idx = lower.find(term)
        if idx != -1:
            start = max(0, idx - max_chars // 3)
            return text[start : start + max_chars].strip()
    return text[:max_chars].strip()


def search_notes(
    query: str,
    allowed_paths: list[Path],
    *,
    restrict_files: list[Path] | None = None,
) -> list[NoteMatch]:
    query = query.strip()
    if not query:
        return []

    query_terms = terms_from_text(query)
    matches: list[NoteMatch] = []
    for file_path in _iter_candidate_files(allowed_paths, restrict_files):
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue

        filename_score = file_path.name.lower().count(query.lower())
        text = _read_searchable_text(file_path)
        content_score = _score_text(text, query) if text else 0
        for term in query_terms:
            content_score += _score_text(text, term) if text else 0
            filename_score += file_path.name.lower().count(term)
        score = filename_score + content_score

        if score == 0:
            continue
        snippet_window = 400 if file_path.suffix.lower() == PDF_SUFFIX else 120
        matches.append(
            NoteMatch(
                path=file_path,
                score=score,
                snippet=_make_snippet(
                    text or file_path.name,
                    query_terms or [query.lower()],
                    window=snippet_window,
                ),
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:MAX_RESULTS]
