from __future__ import annotations

import argparse
import sys

from src import chat
from src.version import VERSION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cadbury",
        description="Cadbury — local personal assistant with strict permissions.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("version", help="Show Cadbury version")
    sub.add_parser("doctor", help="Run health checks")
    sub.add_parser("config", help="Show loaded configuration")
    sub.add_parser("start", help="Start Cadbury (interactive chat)")
    sub.add_parser("interactive", help=argparse.SUPPRESS)  # alias for start
    sub.add_parser("index", help="Build semantic index for allowlisted paths")
    eval_p = sub.add_parser("eval", help="Run retrieval or generation evaluation")
    eval_p.add_argument("--questions", type=str, default=None, help="Path to questions.jsonl")
    eval_p.add_argument("--modes", type=str, default="keyword,semantic,hybrid")
    eval_p.add_argument(
        "--generation",
        action="store_true",
        help="LLM answer eval (slow; needs Ollama). Writes eval/results/generation/",
    )
    eval_p.add_argument("--strict", action="store_true", help="Strict mode for --generation")
    eval_p.add_argument("--limit", type=int, default=None, help="Max questions for --generation")
    eval_p.add_argument(
        "--demo",
        action="store_true",
        help="Public fixture benchmark (no personal config paths)",
    )
    sub.add_parser("listen", help="Listen once and print transcript")

    ask = sub.add_parser("ask", help="Ask with local note retrieval")
    ask.add_argument("question", nargs="+", help="Question text")

    search = sub.add_parser("search", help="Search allowlisted paths")
    search.add_argument("query", nargs="+", help="Search query")

    tool = sub.add_parser("tool", help="Simulate/check a tool permission")
    tool.add_argument("name", help="Tool name, e.g. calendar.read")

    sub.add_parser("calendar", help="Read macOS Calendar (requires calendar.read in config)")

    web = sub.add_parser("web", help="Web search (requires web.search in config)")
    web.add_argument("query", nargs="+", help="Search query")

    wa = sub.add_parser(
        "whatsapp",
        help="Open WhatsApp draft with message (you tap Send; requires whatsapp.draft)",
    )
    wa.add_argument("phone", help="Phone with country code, e.g. +14155551234")
    wa.add_argument("message", nargs="+", help="Message text")

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
    if args.command == "version":
        print(f"cadbury {VERSION}")
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
    if args.command == "eval":
        import sys
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        argv = []
        if args.questions:
            argv.extend(["--questions", args.questions])
        if getattr(args, "demo", False):
            argv.append("--demo")
        if getattr(args, "generation", False):
            from eval.run_gen_eval import main as gen_main

            if args.strict:
                argv.append("--strict")
            if args.limit is not None:
                argv.extend(["--limit", str(args.limit)])
            return gen_main(argv)

        from eval.run_eval import main as eval_main

        if args.modes:
            argv.extend(["--modes", args.modes])
        return eval_main(argv)
    if args.command == "whatsapp":
        print(chat.run_whatsapp(args.phone, " ".join(args.message)))
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
    if args.command == "calendar":
        print(chat.run_calendar())
        return 0
    if args.command == "web":
        print(chat.run_web(" ".join(args.query)))
        return 0
    if args.command == "chat":
        prompt = " ".join(args.prompt)
        print(chat.run_plain_chat(prompt))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
