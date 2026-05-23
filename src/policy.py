from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


AUDIT_LOG_PATH = Path.home() / ".cadbury" / "audit.log"


@dataclass(frozen=True)
class PolicyDecision:
    tool_name: str
    allowed: bool
    reason: str


@dataclass
class SessionPolicy:
    """Tracks per-session tool approvals."""

    approved_tools: set[str] = field(default_factory=set)
    auto_approve_notes: bool = False

    def grant(self, tool_name: str) -> None:
        self.approved_tools.add(tool_name)
        if tool_name == "search_notes":
            self.auto_approve_notes = True

    def is_granted(self, tool_name: str) -> bool:
        if tool_name == "search_notes" and self.auto_approve_notes:
            return True
        return tool_name in self.approved_tools


def can_use_tool(
    tool_name: str,
    *,
    allowed_paths: list[Path] | None = None,
    enabled_tools: frozenset[str] | None = None,
    session: SessionPolicy | None = None,
) -> PolicyDecision:
    if tool_name == "search_notes":
        if not allowed_paths:
            return PolicyDecision(
                tool_name=tool_name,
                allowed=False,
                reason="No allowlisted paths in config.",
            )
        if session and session.is_granted(tool_name):
            return PolicyDecision(
                tool_name=tool_name,
                allowed=True,
                reason="Approved for this session.",
            )
        return PolicyDecision(
            tool_name=tool_name,
            allowed=True,
            reason="Allowed paths configured (approval may still be required).",
        )

    if enabled_tools and tool_name in enabled_tools:
        if session and session.is_granted(tool_name):
            return PolicyDecision(
                tool_name=tool_name,
                allowed=True,
                reason="Approved for this session.",
            )
        return PolicyDecision(
            tool_name=tool_name,
            allowed=True,
            reason="Tool enabled in config (approval may still be required).",
        )

    return PolicyDecision(
        tool_name=tool_name,
        allowed=False,
        reason="Tool is not enabled.",
    )


def auto_approve_tools() -> bool:
    """Non-interactive runs (eval, CI) skip approval prompts when set."""
    return os.environ.get("CADBURY_AUTO_APPROVE", "").strip() in {"1", "true", "yes"}


def request_tool_approval(tool_name: str, *, interactive: bool = True) -> bool:
    if auto_approve_tools():
        return True
    if not interactive:
        return False
    prompt = f"Allow tool '{tool_name}' for this session? [y/N]: "
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def append_audit(event: str, detail: str) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} | {event} | {detail}\n")
