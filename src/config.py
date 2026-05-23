from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATHS = [
    Path.home() / ".cadbury" / "config.yaml",
    PROJECT_ROOT / "config.yaml",
]

DEFAULT_MODEL = "qwen2.5:7b-instruct"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"


@dataclass(frozen=True)
class CadburyConfig:
    model_name: str
    ollama_url: str
    allowed_paths: list[Path]
    require_tool_approval: bool
    strict_mode_default: bool
    enabled_tools: frozenset[str]
    use_embeddings: bool
    embedding_model: str
    voice_enabled: bool
    voice_stt_model: str
    voice_record_seconds: int
    whatsapp_allowed_phones: frozenset[str]


@dataclass(frozen=True)
class LoadedConfig:
    config: CadburyConfig
    source_path: Path | None


def _coerce_paths(raw_paths: list[Any]) -> list[Path]:
    paths: list[Path] = []
    for raw in raw_paths:
        if not isinstance(raw, str):
            continue
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if candidate.exists() and candidate.is_dir():
            paths.append(candidate)
    return paths


def _parse_config(data: dict[str, Any]) -> CadburyConfig:
    raw_paths = data.get("allowed_paths")
    if raw_paths is None:
        raw_paths = data.get("allowed_notes_paths", [])  # legacy key
    if not isinstance(raw_paths, list):
        raw_paths = []

    raw_tools = data.get("enabled_tools", [])
    if not isinstance(raw_tools, list):
        raw_tools = []
    enabled_tools = frozenset(str(t) for t in raw_tools)

    raw_phones = data.get("whatsapp_allowed_phones", [])
    if not isinstance(raw_phones, list):
        raw_phones = []
    whatsapp_allowed_phones = frozenset(
        "".join(ch for ch in str(p) if ch.isdigit()) for p in raw_phones
    )
    whatsapp_allowed_phones = frozenset(p for p in whatsapp_allowed_phones if p)

    return CadburyConfig(
        model_name=str(data.get("model_name", DEFAULT_MODEL)),
        ollama_url=str(data.get("ollama_url", DEFAULT_OLLAMA_URL)),
        allowed_paths=_coerce_paths(raw_paths),
        require_tool_approval=bool(data.get("require_tool_approval", True)),
        strict_mode_default=bool(data.get("strict_mode_default", False)),
        enabled_tools=enabled_tools,
        use_embeddings=bool(data.get("use_embeddings", True)),
        embedding_model=str(data.get("embedding_model", "all-MiniLM-L6-v2")),
        voice_enabled=bool(data.get("voice_enabled", False)),
        voice_stt_model=str(data.get("voice_stt_model", "base.en")),
        voice_record_seconds=int(data.get("voice_record_seconds", 6)),
        whatsapp_allowed_phones=whatsapp_allowed_phones,
    )


def load_config_with_source() -> LoadedConfig:
    data: dict[str, Any] = {}
    source_path: Path | None = None
    for config_path in DEFAULT_CONFIG_PATHS:
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
                if isinstance(loaded, dict):
                    data = loaded
                    source_path = config_path
            break

    return LoadedConfig(config=_parse_config(data), source_path=source_path)


def load_config() -> CadburyConfig:
    return load_config_with_source().config
