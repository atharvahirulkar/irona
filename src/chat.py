from __future__ import annotations

import importlib.util
import sys

import httpx

from src.config import load_config_with_source
from pathlib import Path

from src.notes import get_document_excerpt, search_notes, terms_from_text
from src.rag import build_index, index_exists, semantic_search
from src.voice import listen_once, speak, voice_available
from src.policy import (
    SessionPolicy,
    append_audit,
    can_use_tool,
    request_tool_approval,
)
from src.tools import describe_tool, run_calendar_read, run_web_search

SESSION = SessionPolicy()
# Remember recently used source files for follow-ups like "summarize it".
RECENT_SOURCE_FILES: list[str] = []

SYSTEM_PROMPT = (
    "You are Cadbury, a local assistant running only on this machine. "
    "You do NOT have direct access to files, calendar, email, or the internet. "
    "If you need information from those, you must ask the surrounding application to provide it. "
    "When sources are provided, cite them by file path."
)

INTERACTIVE_HELP = """
Cadbury commands:
  /help          Show this help
  /bye, /exit    Quit
  /notes on|off  Toggle local note retrieval
  /strict on|off Require local sources before answering
  /approve       Approve search_notes for this session
  /config        Show loaded config paths
  /doctor        Run health checks
  /index         Rebuild semantic index
  /listen        Speak for a few seconds (push-to-talk)
  /voice on|off  Speak Cadbury replies aloud (macOS say)
"""


def _loaded():
    return load_config_with_source()


def chat(messages: list[dict[str, str]]) -> str:
    loaded = _loaded()
    cfg = loaded.config
    payload = {
        "model": cfg.model_name,
        "messages": messages,
        "stream": False,
    }
    with httpx.Client(timeout=120) as client:
        resp = client.post(cfg.ollama_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


def _remember_sources(matches: list) -> None:
    RECENT_SOURCE_FILES.clear()
    RECENT_SOURCE_FILES.extend(str(m.path) for m in matches[:3])


def _format_matches_for_prompt(matches: list, question: str) -> str:
    query_terms = terms_from_text(question)
    lines = []
    for index, match in enumerate(matches, start=1):
        lines.append(f"[{index}] {match.path}")
        if index == 1:
            excerpt = get_document_excerpt(Path(match.path), query_terms)
            body = excerpt if excerpt else match.snippet
        else:
            body = match.snippet
        lines.append(f"content: {body}")
    return "\n".join(lines)


def _format_sources(matches: list) -> str:
    lines = ["Sources:"]
    for index, match in enumerate(matches, start=1):
        lines.append(f"- [{index}] {match.path}")
    return "\n".join(lines)


def _is_follow_up(question: str) -> bool:
    q_lower = question.lower()
    return any(
        phrase in q_lower
        for phrase in (" it", "this", "that", "the file", "the document", "contents of")
    )


def _build_search_queries(question: str) -> list[str]:
    """Build search queries only from the user's words and recent context."""
    queries = [question]
    for term in terms_from_text(question):
        queries.append(term)
    if _is_follow_up(question) and RECENT_SOURCE_FILES:
        for file_path in RECENT_SOURCE_FILES:
            queries.append(Path(file_path).name)

    seen: set[str] = set()
    ordered: list[str] = []
    for query in queries:
        key = query.strip().lower()
        if key and key not in seen:
            seen.add(key)
            ordered.append(query)
    return ordered


def _merge_matches(match_lists: list[list]) -> list:
    best: dict[str, object] = {}
    for matches in match_lists:
        for match in matches:
            key = str(match.path)
            existing = best.get(key)
            if existing is None or match.score > existing.score:
                best[key] = match
    merged = list(best.values())
    merged.sort(key=lambda m: m.score, reverse=True)
    return merged[:5]


def _search_with_fallback(question: str, allowed_paths: list) -> list:
    loaded = _loaded()
    cfg = loaded.config
    restrict_files = None
    if _is_follow_up(question) and RECENT_SOURCE_FILES:
        restrict_files = [Path(path) for path in RECENT_SOURCE_FILES]

    all_lists: list[list] = []

    if cfg.use_embeddings and index_exists():
        all_lists.append(
            semantic_search(question, restrict_files=restrict_files, top_k=5)
        )

    if restrict_files:
        focused = search_notes(
            query=question,
            allowed_paths=allowed_paths,
            restrict_files=restrict_files,
        )
        if focused:
            all_lists.append(focused)

    for q in _build_search_queries(question):
        all_lists.append(search_notes(query=q, allowed_paths=allowed_paths))

    return _merge_matches(all_lists)


def run_listen() -> str:
    loaded = _loaded()
    cfg = loaded.config
    if not cfg.voice_enabled:
        return "Voice is disabled in config (voice_enabled: false)."
    try:
        transcript = listen_once(cfg.voice_stt_model, cfg.voice_record_seconds)
    except Exception as exc:
        return f"Voice error: {exc}"
    if not transcript:
        return "No speech detected."
    append_audit("voice_transcript", transcript)
    return transcript


def _respond(user_input: str, *, notes_enabled: bool, strict_mode: bool, history: list) -> str:
    if notes_enabled:
        return run_ask(user_input, strict=strict_mode)
    history.append({"role": "user", "content": user_input})
    response = chat(history)
    history.append({"role": "assistant", "content": response})
    return response


def run_index() -> str:
    loaded = _loaded()
    cfg = loaded.config
    if not cfg.allowed_paths:
        return "No allowlisted paths configured. Edit config.yaml first."
    return build_index(cfg.allowed_paths, model_name=cfg.embedding_model)


def _ensure_tool_allowed(tool_name: str, *, query: str = "") -> tuple[bool, str]:
    loaded = _loaded()
    cfg = loaded.config
    decision = can_use_tool(
        tool_name,
        allowed_paths=cfg.allowed_paths,
        enabled_tools=cfg.enabled_tools,
        session=SESSION,
    )
    append_audit(
        "tool_request",
        (
            f"tool={decision.tool_name} allowed={decision.allowed} "
            f"reason={decision.reason} query={query}"
        ),
    )
    if not decision.allowed:
        return False, describe_tool(tool_name, decision)

    if cfg.require_tool_approval and not SESSION.is_granted(tool_name):
        if not request_tool_approval(tool_name):
            append_audit("tool_denied", f"tool={tool_name} user_denied=true")
            return False, f"Tool '{tool_name}' denied by user."
        SESSION.grant(tool_name)
        append_audit("tool_granted", f"tool={tool_name} session=true")

    return True, ""


def simulate_tool_request(tool_name: str) -> str:
    loaded = _loaded()
    cfg = loaded.config
    decision = can_use_tool(
        tool_name,
        allowed_paths=cfg.allowed_paths,
        enabled_tools=cfg.enabled_tools,
        session=SESSION,
    )
    append_audit(
        "tool_request",
        f"tool={decision.tool_name} allowed={decision.allowed} reason={decision.reason}",
    )
    if tool_name == "calendar.read" and decision.allowed:
        return run_calendar_read()
    if tool_name == "web.search" and decision.allowed:
        return run_web_search("example")
    return describe_tool(tool_name, decision)


def run_search_notes(query: str) -> str:
    ok, msg = _ensure_tool_allowed("search_notes", query=query)
    if not ok:
        return msg

    loaded = _loaded()
    matches = search_notes(query=query, allowed_paths=loaded.config.allowed_paths)
    append_audit("tool_result", f"tool=search_notes matches={len(matches)} query={query}")
    if not matches:
        return "No matching files found in allowlisted paths."

    lines = ["Top matches:"]
    for match in matches:
        lines.append(f"- {match.path} (score={match.score})")
        lines.append(f"  snippet: {match.snippet}")
    return "\n".join(lines)


def run_ask(question: str, *, strict: bool = False) -> str:
    ok, msg = _ensure_tool_allowed("search_notes", query=question)
    if not ok:
        if strict:
            return msg
        return run_plain_chat(question)

    loaded = _loaded()
    matches = _search_with_fallback(question, loaded.config.allowed_paths)
    append_audit("tool_result", f"tool=search_notes matches={len(matches)} query={question}")

    if strict and not matches:
        return (
            "Strict mode: no local sources matched your question. "
            "Refine your query or disable strict mode."
        )

    if matches:
        _remember_sources(matches)
        context_block = _format_matches_for_prompt(matches, question)
        user_content = (
            f"Question: {question}\n\n"
            "Use only the context below when answering. "
            "If context is insufficient, say so clearly.\n\n"
            f"Context:\n{context_block}"
        )
    else:
        user_content = (
            f"Question: {question}\n\n"
            "No local context was found. Answer generally and mention that no local notes matched."
        )

    response = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
    )
    if matches:
        return f"{response}\n\n{_format_sources(matches)}"
    return response


def run_plain_chat(prompt: str) -> str:
    append_audit("chat_prompt", prompt)
    response = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )
    append_audit("chat_response", response)
    return response


def show_config() -> str:
    loaded = _loaded()
    cfg = loaded.config
    lines = [
        f"Config source: {loaded.source_path or 'none'}",
        f"Model: {cfg.model_name}",
        f"Ollama URL: {cfg.ollama_url}",
        f"Require tool approval: {cfg.require_tool_approval}",
        f"Strict mode default: {cfg.strict_mode_default}",
        f"Enabled tools: {', '.join(sorted(cfg.enabled_tools)) or '(none)'}",
        "Allowed paths:",
    ]
    if not cfg.allowed_paths:
        lines.append("- (none)")
    else:
        for path in cfg.allowed_paths:
            lines.append(f"- {path}")
    return "\n".join(lines)


def doctor() -> str:
    loaded = _loaded()
    cfg = loaded.config
    lines = [
        "Cadbury doctor (v0.1)",
        f"- model: {cfg.model_name}",
        f"- ollama url: {cfg.ollama_url}",
        f"- config source: {loaded.source_path or 'none'}",
        f"- allowlisted paths: {len(cfg.allowed_paths)}",
        f"- require approval: {cfg.require_tool_approval}",
        f"- pypdf installed: {importlib.util.find_spec('pypdf') is not None}",
        f"- python-docx installed: {importlib.util.find_spec('docx') is not None}",
        f"- embeddings enabled: {cfg.use_embeddings}",
        f"- rag index present: {index_exists()}",
        f"- voice available: {voice_available()}",
        f"- voice enabled: {cfg.voice_enabled}",
    ]
    for path in cfg.allowed_paths:
        lines.append(f"  - {path} (exists={path.exists()})")

    try:
        with httpx.Client(timeout=5) as client:
            client.get(cfg.ollama_url.replace("/api/chat", "/api/tags"))
        lines.append("- ollama reachable: yes")
    except Exception:
        lines.append("- ollama reachable: no (start Ollama app)")

    return "\n".join(lines)


def run_interactive() -> None:
    loaded = _loaded()
    strict_mode = loaded.config.strict_mode_default
    notes_enabled = True

    print("Cadbury (v0.2)")
    print("Type /help for commands. /bye to quit.")
    if voice_available() and loaded.config.voice_enabled:
        print("Voice: /listen to talk, /voice on for spoken replies.")
    history: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    voice_replies = False

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in {"/bye", "/exit", "exit", "quit"}:
            print("bye.")
            break
        if cmd == "/help":
            print(INTERACTIVE_HELP)
            continue
        if cmd == "/notes on":
            notes_enabled = True
            print("cadbury> notes retrieval enabled.")
            continue
        if cmd == "/notes off":
            notes_enabled = False
            print("cadbury> notes retrieval disabled.")
            continue
        if cmd == "/strict on":
            strict_mode = True
            print("cadbury> strict mode enabled.")
            continue
        if cmd == "/strict off":
            strict_mode = False
            print("cadbury> strict mode disabled.")
            continue
        if cmd == "/approve":
            SESSION.grant("search_notes")
            print("cadbury> search_notes approved for this session.")
            continue
        if cmd == "/config":
            print(show_config())
            continue
        if cmd == "/doctor":
            print(doctor())
            continue
        if cmd == "/index":
            print(run_index())
            continue
        if cmd == "/listen":
            transcript = run_listen()
            print(f"you (voice)> {transcript}")
            if not transcript or transcript.startswith(("Voice", "No speech")):
                continue
            user_input = transcript
        elif cmd == "/voice on":
            voice_replies = True
            print("cadbury> spoken replies enabled.")
            continue
        elif cmd == "/voice off":
            voice_replies = False
            print("cadbury> spoken replies disabled.")
            continue
        else:
            user_input = user_input

        append_audit("interactive_prompt", user_input)
        response = _respond(user_input, notes_enabled=notes_enabled, strict_mode=strict_mode, history=history)
        append_audit("interactive_response", response)
        print(f"cadbury> {response}\n")
        if voice_replies and voice_available():
            speak(response)


def _legacy_main(argv: list[str]) -> int:
    """Backward-compatible flags used during early setup."""
    if argv[0] == "--show-config":
        print(show_config())
        return 0
    if argv[0] == "--doctor":
        print(doctor())
        return 0
    if argv[0] == "--interactive":
        run_interactive()
        return 0
    if argv[0] == "--request-tool":
        if len(argv) < 2:
            print('Usage: --request-tool "tool.name"')
            return 1
        print(simulate_tool_request(" ".join(argv[1:])))
        return 0
    if argv[0] == "--search-notes":
        if len(argv) < 2:
            print('Usage: --search-notes "query"')
            return 1
        print(run_search_notes(" ".join(argv[1:])))
        return 0
    if argv[0] == "--ask":
        if len(argv) < 2:
            print('Usage: --ask "question"')
            return 1
        question = " ".join(argv[1:])
        append_audit("ask_prompt", question)
        print(run_ask(question))
        return 0
    print(run_plain_chat(" ".join(argv)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1].startswith("-"):
        raise SystemExit(_legacy_main(sys.argv[1:]))
    from src.cli import main

    raise SystemExit(main())
