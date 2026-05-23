#!/usr/bin/env python3
"""Generation eval: hybrid retrieval + Ollama answer vs gold terms.

Sets CADBURY_AUTO_APPROVE=1 so tools run without prompts.
Requires Ollama running. Slower than retrieval-only eval.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from eval.paths import FIXTURE_CORPUS, GEN_RESULTS
from eval.run_eval import Question, _load_questions, _resolve_questions
from src.chat import SESSION, run_ask
from src.config import load_config_with_source


@dataclass
class GenQuestionResult:
    id: str
    answer_ok: bool
    citation_ok: bool
    latency_ms: float
    answer_preview: str


def _answer_has_terms(text: str, terms: list[str]) -> bool:
    if not terms:
        return True
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _answer_cites_source(text: str, expected_sources: list[str]) -> bool:
    if not expected_sources:
        return True
    lower = text.lower()
    return any(src.lower() in lower for src in expected_sources)


def run_generation_eval(
    questions: list[Question],
    *,
    strict: bool,
    limit: int | None,
) -> dict:
    os.environ["CADBURY_AUTO_APPROVE"] = "1"
    SESSION.grant("search_notes")

    subset = questions[:limit] if limit else questions
    scored: list[GenQuestionResult] = []
    skipped = 0

    for item in subset:
        answer_terms = list(item.expected_answer_terms or [])
        if not answer_terms:
            answer_terms = list(item.expected_terms or [])
        if not answer_terms:
            skipped += 1
            continue

        start = time.perf_counter()
        try:
            response = run_ask(item.question, strict=strict, use_files=True)
        except Exception as exc:
            response = f"ERROR: {exc}"
        elapsed_ms = (time.perf_counter() - start) * 1000

        row = GenQuestionResult(
            id=item.id,
            answer_ok=_answer_has_terms(response, answer_terms),
            citation_ok=_answer_cites_source(response, item.expected_sources),
            latency_ms=round(elapsed_ms, 1),
            answer_preview=response.replace("\n", " ")[:200],
        )
        scored.append(row)

    n = len(scored) or 1
    return {
        "questions_total": len(subset),
        "questions_scored": len(scored),
        "questions_skipped": skipped,
        "strict": strict,
        "answer_accuracy": sum(1 for r in scored if r.answer_ok) / n,
        "citation_rate": sum(1 for r in scored if r.citation_ok) / n,
        "avg_latency_ms": round(sum(r.latency_ms for r in scored) / n, 1),
        "details": [asdict(r) for r in scored],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cadbury generation evaluation (LLM)")
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Require retrieved context")
    parser.add_argument("--limit", type=int, default=None, help="Max questions to run")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use public fixture corpus + template questions",
    )
    args = parser.parse_args(argv)

    if args.demo:
        config_label = f"demo ({FIXTURE_CORPUS})"
    else:
        loaded = load_config_with_source()
        if not loaded.config.allowed_paths:
            print("No allowlisted paths in config.")
            return 1
        config_label = str(loaded.source_path or "config")

    questions_path = _resolve_questions(args.questions, demo=args.demo)
    questions = _load_questions(questions_path)
    if not questions:
        print(f"No questions in {questions_path}")
        return 1

    print(f"Cadbury generation eval — {len(questions)} questions")
    print(f"Config: {config_label} | strict={args.strict}")
    print("(Requires Ollama — calls LLM per scored question)\n")

    result = run_generation_eval(questions, strict=args.strict, limit=args.limit)

    print(f"Scored: {result['questions_scored']} (skipped {result['questions_skipped']} without gold terms)")
    print(f"Answer accuracy: {result['answer_accuracy']:.0%}")
    print(f"Citation rate:   {result['citation_rate']:.0%}")
    print(f"Avg latency:     {result['avg_latency_ms']:.0f} ms")

    GEN_RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {"timestamp": stamp, "questions_file": str(questions_path), **result}
    out = GEN_RESULTS / f"{stamp}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (GEN_RESULTS / "latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (GEN_RESULTS / "latest.md").write_text(
        f"# Generation eval ({stamp})\n\n"
        f"- Answer accuracy: **{result['answer_accuracy']:.0%}**\n"
        f"- Citation rate: **{result['citation_rate']:.0%}**\n"
        f"- Avg latency: {result['avg_latency_ms']:.0f} ms\n",
        encoding="utf-8",
    )
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
