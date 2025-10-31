"""Command-line interface for the mddiff library."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from .diff import diff
from .models import InlineDiffConfig
from .render import render_unified
from .render_html import HtmlRenderOptions, render_html


def main(argv: Iterable[str] | None = None) -> int:
    """Entry point for the ``mddiff`` CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.left == "-" and args.right == "-":
        parser.error("Cannot read both inputs from stdin")

    left_text, left_id = _load_input(args.left)
    right_text, right_id = _load_input(args.right)

    inline_config = _build_inline_config(args)

    try:
        result = diff(
            left_text,
            right_text,
            left_id=left_id,
            right_id=right_id,
            inline_config=inline_config,
            context=args.context,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if result.has_changes:
        if args.format == "text":
            output = render_unified(result)
        else:
            layout = "unified" if args.format == "html-unified" else "split"
            html_options = HtmlRenderOptions(layout=layout)
            output = render_html(result, options=html_options)
        if output:
            sys.stdout.write(output)
            if not output.endswith("\n"):
                sys.stdout.write("\n")
    return 1 if result.has_changes else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mddiff",
        description="Unified Markdown diff with normalization-aware comparison.",
    )
    parser.add_argument("left", help="Path to the left (original) Markdown document or '-' for stdin")
    parser.add_argument("right", help="Path to the right (updated) Markdown document or '-' for stdin")
    parser.add_argument(
        "--context",
        type=int,
        default=None,
        help="Number of unchanged context lines to include around differences.",
    )
    parser.add_argument(
        "--inline-min-real-quick",
        type=float,
        default=None,
        help="Minimum difflib real_quick_ratio required to emit inline edits (default: 0.2).",
    )
    parser.add_argument(
        "--inline-min-quick",
        type=float,
        default=None,
        help="Minimum difflib quick_ratio required to emit inline edits (default: 0.3).",
    )
    parser.add_argument(
        "--inline-min-ratio",
        type=float,
        default=None,
        help="Minimum difflib ratio required to emit inline edits (default: 0.35).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "html-split", "html-unified"),
        default="text",
        help="Output format for changes (default: text).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_resolve_version()}",
    )
    return parser


def _load_input(identifier: str) -> tuple[str, str]:
    if identifier == "-":
        data = sys.stdin.read()
        return data, "stdin"
    path = Path(identifier)
    text = path.read_text(encoding="utf-8")
    return text, str(path)


def _build_inline_config(args: argparse.Namespace) -> InlineDiffConfig | None:
    provided = [
        args.inline_min_real_quick,
        args.inline_min_quick,
        args.inline_min_ratio,
    ]
    if not any(value is not None for value in provided):
        return None

    defaults = InlineDiffConfig()
    return InlineDiffConfig(
        min_real_quick_ratio=(
            args.inline_min_real_quick
            if args.inline_min_real_quick is not None
            else defaults.min_real_quick_ratio
        ),
        min_quick_ratio=(
            args.inline_min_quick
            if args.inline_min_quick is not None
            else defaults.min_quick_ratio
        ),
        min_ratio=(
            args.inline_min_ratio
            if args.inline_min_ratio is not None
            else defaults.min_ratio
        ),
    )


def _resolve_version() -> str:
    try:  # pragma: no cover - importlib metadata availability depends on packaging context
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover
        return "0.0.0"

    try:
        return version("mddiff")
    except PackageNotFoundError:
        return "0.0.0"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
