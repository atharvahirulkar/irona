from __future__ import annotations

import argparse
import sys

from src import chat


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cadbury",
        description="Cadbury — local personal assistant with strict permissions.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("doctor", help="Run health checks")
    sub.add_parser("config", help="Show loaded configuration")
    sub.add_parser("start", help="Start Cadbury (interactive chat)")
    sub.add_parser("interactive", help=argparse.SUPPRESS)  # alias for start
    sub.add_parser("index", help="Build semantic index for allowlisted paths")
    sub.add_parser("listen", help="Listen once and print transcript")

    ask = sub.add_parser("ask", help="Ask with local note retrieval")
    ask.add_argument("question", nargs="+", help="Question text")

    search = sub.add_parser("search", help="Search allowlisted paths")
    search.add_argument("query", nargs="+", help="Search query")

    tool = sub.add_parser("tool", help="Simulate/check a tool permission")
    tool.add_argument("name", help="Tool name, e.g. calendar.read")

    chat_cmd = sub.add_parser("chat", help="Plain chat without retrieval")
    chat_cmd.add_argument("prompt", nargs="+", help="Prompt text")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        chat.run_interactive()
        return 0

    if args.command in {"start", "interactive"}:
        chat.run_interactive()
        return 0
    if args.command == "doctor":
        print(chat.doctor())
        return 0
    if args.command == "config":
        print(chat.show_config())
        return 0
    if args.command == "index":
        print(chat.run_index())
        return 0
    if args.command == "listen":
        print(chat.run_listen())
        return 0
    if args.command == "ask":
        question = " ".join(args.question)
        print(chat.run_ask(question))
        return 0
    if args.command == "search":
        query = " ".join(args.query)
        print(chat.run_search_notes(query))
        return 0
    if args.command == "tool":
        print(chat.simulate_tool_request(args.name))
        return 0
    if args.command == "chat":
        prompt = " ".join(args.prompt)
        print(chat.run_plain_chat(prompt))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
