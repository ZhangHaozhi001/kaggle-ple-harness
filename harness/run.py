"""CLI entry point.

Usage:
  python -m harness.run score  --tasks sample_tasks [--model mock] [--out results.json]
  python -m harness.run check  --tasks sample_tasks --answers answers_dir

Only the mock model is runnable in this skeleton; the real model client
refuses to run until explicitly enabled in a later segment (no API cost).
"""
from __future__ import annotations

import argparse
import json
import sys

from .model import MockModelClient, ModelNotConfigured, VertexModelClient
from .scorer import run_scoring, run_self_check


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_score = sub.add_parser("score", help="run agent + local scorer over a task dir")
    p_score.add_argument("--tasks", required=True)
    p_score.add_argument("--model", default="mock", choices=["mock", "vertex"])
    p_score.add_argument("--out", default=None)

    p_check = sub.add_parser("check", help="pre-submission structural self-check")
    p_check.add_argument("--tasks", required=True)
    p_check.add_argument("--answers", required=True)

    args = ap.parse_args(argv)

    if args.cmd == "score":
        try:
            model = MockModelClient() if args.model == "mock" else VertexModelClient()
        except ModelNotConfigured as e:
            print(f"model unavailable: {e}", file=sys.stderr)
            return 2
        report = run_scoring(args.tasks, model)
        text = json.dumps(report, indent=2, ensure_ascii=False)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text + "\n")
        print(text)
        return 0

    if args.cmd == "check":
        report = run_self_check(args.tasks, args.answers)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["all_complete"] else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
