from __future__ import annotations

from src.policy import PolicyDecision, append_audit


def run_calendar_read() -> str:
    append_audit("tool_result", "tool=calendar.read status=not_implemented")
    return "calendar.read is not implemented in v0.1."


def run_web_search(query: str) -> str:
    append_audit("tool_result", f"tool=web.search status=not_implemented query={query}")
    return "web.search is disabled in v0.1."


def describe_tool(tool_name: str, decision: PolicyDecision) -> str:
    return (
        f"Tool '{tool_name}' allowed={decision.allowed}. "
        f"Reason: {decision.reason}"
    )
