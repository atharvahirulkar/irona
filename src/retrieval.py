"""Retrieval strategies for Irona (keyword, semantic, hybrid).

Separated from chat so evaluation and production share the same code paths.
"""

from __future__ import annotations

from pathlib import Path

from src.notes import NoteMatch, search_notes, terms_from_text
from src.rag import index_exists, semantic_search


def merge_matches(match_lists: list[list[NoteMatch]]) -> list[NoteMatch]:
    best: dict[str, NoteMatch] = {}
    for matches in match_lists:
        for match in matches:
            key = str(match.path)
            existing = best.get(key)
            if existing is None or match.score > existing.score:
                best[key] = match
    merged = list(best.values())
    merged.sort(key=lambda m: m.score, reverse=True)
    return merged[:5]


def _keyword_queries(question: str) -> list[str]:
    queries = [question]
    for term in terms_from_text(question):
        queries.append(term)
    seen: set[str] = set()
    ordered: list[str] = []
    for query in queries:
        key = query.strip().lower()
        if key and key not in seen:
            seen.add(key)
            ordered.append(query)
    return ordered


def search_keyword(
    question: str,
    allowed_paths: list[Path],
    *,
    restrict_files: list[Path] | None = None,
) -> list[NoteMatch]:
    """Keyword + filename scoring only (no embedding index)."""
    lists: list[list[NoteMatch]] = []
    for query in _keyword_queries(question):
        lists.append(
            search_notes(
                query=query,
                allowed_paths=allowed_paths,
                restrict_files=restrict_files,
            )
        )
    return merge_matches(lists)


def search_semantic(
    question: str,
    *,
    restrict_files: list[Path] | None = None,
    top_k: int = 5,
) -> list[NoteMatch]:
    """Semantic search only; empty if index missing."""
    if not index_exists():
        return []
    return semantic_search(question, restrict_files=restrict_files, top_k=top_k)


def search_hybrid(
    question: str,
    allowed_paths: list[Path],
    *,
    use_embeddings: bool = True,
    restrict_files: list[Path] | None = None,
    extra_queries: list[str] | None = None,
) -> list[NoteMatch]:
    """Production retrieval: semantic (if enabled) + keyword fan-out."""
    lists: list[list[NoteMatch]] = []

    if use_embeddings and index_exists():
        lists.append(
            semantic_search(question, restrict_files=restrict_files, top_k=5)
        )

    if restrict_files:
        focused = search_notes(
            query=question,
            allowed_paths=allowed_paths,
            restrict_files=restrict_files,
        )
        if focused:
            lists.append(focused)

    queries = _keyword_queries(question)
    if extra_queries:
        for q in extra_queries:
            if q.strip().lower() not in {x.strip().lower() for x in queries}:
                queries.append(q)

    for query in queries:
        lists.append(
            search_notes(
                query=query,
                allowed_paths=allowed_paths,
                restrict_files=restrict_files,
            )
        )

    return merge_matches(lists)
