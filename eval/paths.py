"""Paths for evaluation (public templates vs personal user data)."""

from __future__ import annotations

from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_ROOT.parent

USER_QUESTIONS = PROJECT_ROOT / "user" / "questions.jsonl"
TEMPLATE_QUESTIONS = EVAL_ROOT / "questions.template.jsonl"
FIXTURE_CORPUS = EVAL_ROOT / "fixtures" / "corpus"
LEGACY_QUESTIONS = EVAL_ROOT / "questions.jsonl"
RESULTS_DIR = EVAL_ROOT / "results"
GEN_RESULTS = RESULTS_DIR / "generation"
