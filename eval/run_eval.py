#!/usr/bin/env python3
"""Measure Cadbury retrieval quality (keyword vs semantic vs hybrid).

Does not call the LLM — only retrieval — so results are fast and reproducible.
See EVAL.md for how to build your gold question set.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from eval.paths import (
    FIXTURE_CORPUS,
    LEGACY_QUESTIONS,
    RESULTS_DIR,
    TEMPLATE_QUESTIONS,
    USER_QUESTIONS,
)
from src.config import load_config_with_source
from src.notes import NoteMatch
from src.retrieval import search_hybrid, search_keyword, search_semantic

MODES = {
    "keyword": lambda q, paths, use_emb: search_keyword(q, paths),
    "semantic": lambda q, paths, use_emb: search_semantic(q),
    "hybrid": lambda q, paths, use_emb: search_hybrid(q, paths, use_embeddings=use_emb),
}


@dataclass
class Question:
    id: str
    question: str
    expected_sources: list[str]
    expected_terms: list[str]
    expected_answer_terms: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict) -> Question:
        return cls(
            id=str(raw["id"]),
            question=str(raw["question"]).strip(),
            expected_sources=[str(s) for s in raw.get("expected_sources", [])],
            expected_terms=[str(t) for t in raw.get("expected_terms", [])],
            expected_answer_terms=[
                str(t) for t in raw.get("expected_answer_terms", [])
            ],
            notes=str(raw.get("notes", "")),
        )


@dataclass
class QuestionResult:
    id: str
    hit_at_1: bool
    hit_at_5: bool
    reciprocal_rank: float
    top_path: str | None
    latency_ms: float


def _load_questions(path: Path) -> list[Question]:
    questions: list[Question] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        questions.append(Question.from_dict(json.loads(line)))
    return questions


def _source_hit(match: NoteMatch, expected_sources: list[str]) -> bool:
    path_str = str(match.path)
    name = match.path.name
    for expected in expected_sources:
        if expected in path_str or name == expected or name.endswith(expected):
            return True
    return False


def _terms_ok(match: NoteMatch, expected_terms: list[str]) -> bool:
    if not expected_terms:
        return True
    blob = f"{match.path.name} {match.snippet}".lower()
    return any(term.lower() in blob for term in expected_terms)


def _score_question(
    matches: list[NoteMatch],
    expected_sources: list[str],
    expected_terms: list[str],
) -> QuestionResult:
    hit_rank: int | None = None
    for rank, match in enumerate(matches[:5], start=1):
        if not expected_sources:
            break
        if _source_hit(match, expected_sources) and _terms_ok(match, expected_terms):
            hit_rank = rank
            break

    top_path = str(matches[0].path) if matches else None
    return QuestionResult(
        id="",
        hit_at_1=hit_rank == 1,
        hit_at_5=hit_rank is not None,
        reciprocal_rank=(1.0 / hit_rank) if hit_rank else 0.0,
        top_path=top_path,
        latency_ms=0.0,
    )


def run_mode(
    mode: str,
    questions: list[Question],
    allowed_paths: list[Path],
    *,
    use_embeddings: bool,
) -> dict:
    runner = MODES[mode]
    per_question: list[dict] = []
    t0 = time.perf_counter()

    for item in questions:
        start = time.perf_counter()
        matches = runner(item.question, allowed_paths, use_embeddings)
        elapsed_ms = (time.perf_counter() - start) * 1000
        scored = _score_question(matches, item.expected_sources, item.expected_terms)
        scored.id = item.id
        scored.latency_ms = round(elapsed_ms, 1)
        per_question.append(asdict(scored))

    total_ms = (time.perf_counter() - t0) * 1000
    n = len(questions) or 1
    return {
        "mode": mode,
        "questions": len(questions),
        "recall_at_1": sum(1 for r in per_question if r["hit_at_1"]) / n,
        "recall_at_5": sum(1 for r in per_question if r["hit_at_5"]) / n,
        "mrr": sum(r["reciprocal_rank"] for r in per_question) / n,
        "avg_latency_ms": round(
            sum(r["latency_ms"] for r in per_question) / n, 1
        ),
        "total_ms": round(total_ms, 1),
        "details": per_question,
    }


def _resolve_questions(path: Path | None, *, demo: bool = False) -> Path:
    if demo:
        if not TEMPLATE_QUESTIONS.exists():
            raise FileNotFoundError(f"Missing {TEMPLATE_QUESTIONS}")
        return TEMPLATE_QUESTIONS
    if path and path.exists():
        return path
    if USER_QUESTIONS.exists():
        return USER_QUESTIONS
    if LEGACY_QUESTIONS.exists():
        print(
            "Note: using eval/questions.jsonl (legacy). "
            "Prefer user/questions.jsonl — run ./scripts/init-user.sh"
        )
        return LEGACY_QUESTIONS
    raise FileNotFoundError(
        "No personal eval set found. Run ./scripts/init-user.sh "
        "or cadbury eval --demo for the public fixture benchmark."
    )


def _markdown_table(summaries: list[dict]) -> str:
    lines = [
        "| Mode | Recall@1 | Recall@5 | MRR | Avg latency (ms) |",
        "|------|----------|----------|-----|------------------|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['mode']} | {row['recall_at_1']:.0%} | {row['recall_at_5']:.0%} | "
            f"{row['mrr']:.3f} | {row['avg_latency_ms']:.0f} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cadbury retrieval evaluation")
    parser.add_argument(
        "--questions",
        type=Path,
        default=None,
        help="JSONL gold questions (default: eval/questions.jsonl or example)",
    )
    parser.add_argument(
        "--modes",
        default="keyword,semantic,hybrid",
        help="Comma-separated: keyword, semantic, hybrid",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON results (default: eval/results/<timestamp>.json)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Public benchmark: eval/fixtures/corpus + questions.template.jsonl",
    )
    args = parser.parse_args(argv)

    if args.demo:
        allowed_paths = [FIXTURE_CORPUS.resolve()]
        use_embeddings = True
        config_label = f"demo corpus ({FIXTURE_CORPUS})"
        questions_path = _resolve_questions(args.questions, demo=True)
    else:
        loaded = load_config_with_source()
        cfg = loaded.config
        if not cfg.allowed_paths:
            print("No allowlisted paths in config. Set allowed_paths in config.yaml.")
            return 1
        allowed_paths = cfg.allowed_paths
        use_embeddings = cfg.use_embeddings
        config_label = str(loaded.source_path or "config")
        questions_path = _resolve_questions(args.questions, demo=False)
    questions = _load_questions(questions_path)
    if not questions:
        print(f"No questions in {questions_path}")
        return 1

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for mode in modes:
        if mode not in MODES:
            print(f"Unknown mode: {mode}. Choose from: {', '.join(MODES)}")
            return 1

    print(f"Cadbury eval — {len(questions)} questions from {questions_path}")
    print(f"Config: {config_label} | allowlisted roots: {len(allowed_paths)}")
    print()

    summaries: list[dict] = []
    all_details: dict[str, dict] = {}

    for mode in modes:
        result = run_mode(
            mode,
            questions,
            allowed_paths,
            use_embeddings=use_embeddings,
        )
        summaries.append({k: result[k] for k in ("mode", "recall_at_1", "recall_at_5", "mrr", "avg_latency_ms")})
        all_details[mode] = result
        print(
            f"{mode:8}  recall@1={result['recall_at_1']:.0%}  "
            f"recall@5={result['recall_at_5']:.0%}  mrr={result['mrr']:.3f}  "
            f"avg={result['avg_latency_ms']:.0f}ms"
        )

    print()
    print(_markdown_table(summaries))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = args.output or (RESULTS_DIR / f"{stamp}.json")
    payload = {
        "timestamp": stamp,
        "questions_file": str(questions_path),
        "config_source": config_label,
        "demo": args.demo,
        "use_embeddings": use_embeddings,
        "summary": summaries,
        "modes": all_details,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = RESULTS_DIR / "latest.json"
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (RESULTS_DIR / "latest.md").write_text(
        f"# Cadbury eval ({stamp})\n\n{_markdown_table(summaries)}\n",
        encoding="utf-8",
    )
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
