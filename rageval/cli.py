"""
RAGeval CLI — `rageval init` and `rageval serve` entrypoints.
"""
from __future__ import annotations

import argparse
import sys

from .store import init_rageval_table


def main() -> None:
    p = argparse.ArgumentParser(prog="rageval")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("init", help="Initialize the RAGeval DB")

    s = sub.add_parser("serve", help="Run the RAGeval API server")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8003)

    args = p.parse_args()
    if args.cmd == "init":
        init_rageval_table()
        print("RAGeval DB initialized.")
        return
    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("api:app", host=args.host, port=args.port, reload=False)
        return
    p.print_help()


if __name__ == "__main__":
    main()
