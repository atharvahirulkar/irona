from __future__ import annotations


def wants_calendar(question: str) -> bool:
    q = question.lower()
    hints = (
        "calendar",
        "schedule",
        "meeting",
        "appointment",
        "event",
        "tomorrow",
        "today",
        "this week",
        "next week",
        "what's on",
        "whats on",
    )
    return any(hint in q for hint in hints)


def wants_web(question: str) -> bool:
    q = question.lower()
    hints = (
        "search the web",
        "look up online",
        "on the internet",
        "latest news",
        "current news",
        "weather",
        "stock price",
        "web search",
    )
    return any(hint in q for hint in hints)
