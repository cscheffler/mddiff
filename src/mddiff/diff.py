"""Line-level diff engine for normalized Markdown documents."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable, List

from .inline import diff_inline
from .models import ChangeType, DiffLine, DiffResult, NormalizedDocument
from .normalize import normalize


def diff(
    left: str | NormalizedDocument,
    right: str | NormalizedDocument,
    *,
    left_id: str = "left",
    right_id: str = "right"
) -> DiffResult:
    """Normalize inputs as needed and compute a unified diff."""

    left_doc = left if isinstance(left, NormalizedDocument) else normalize(left, source_id=left_id)
    right_doc = right if isinstance(right, NormalizedDocument) else normalize(right, source_id=right_id)
    return diff_normalized(left_doc, right_doc)


def diff_normalized(left: NormalizedDocument, right: NormalizedDocument) -> DiffResult:
    """Compute a diff between two already-normalized documents."""

    matcher = SequenceMatcher(None, left.lines, right.lines, autojunk=False)
    lines: List[DiffLine] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            lines.extend(
                _build_unchanged_lines(left, right, i1, i2, j1)
            )
        elif tag == "delete":
            lines.extend(_build_deleted_lines(left, i1, i2))
        elif tag == "insert":
            lines.extend(_build_inserted_lines(right, j1, j2))
        elif tag == "replace":
            lines.extend(
                _build_replaced_lines(left, right, i1, i2, j1, j2)
            )
        else:  # pragma: no cover - defensive guard
            raise ValueError(f"Unexpected opcode: {tag}")

    return DiffResult(left=left, right=right, lines=tuple(lines))


def _build_unchanged_lines(
    left: NormalizedDocument,
    right: NormalizedDocument,
    i1: int,
    i2: int,
    j1: int,
) -> Iterable[DiffLine]:
    for offset, left_idx in enumerate(range(i1, i2)):
        right_idx = j1 + offset
        line_text = left.lines[left_idx]
        yield DiffLine(
            kind=ChangeType.UNCHANGED,
            left_lineno=left_idx + 1,
            right_lineno=right_idx + 1,
            left_text=line_text,
            right_text=right.lines[right_idx],
        )


def _build_deleted_lines(
    left: NormalizedDocument,
    i1: int,
    i2: int,
) -> Iterable[DiffLine]:
    for left_idx in range(i1, i2):
        line_text = left.lines[left_idx]
        yield DiffLine(
            kind=ChangeType.DELETED,
            left_lineno=left_idx + 1,
            right_lineno=None,
            left_text=line_text,
            right_text=None,
        )


def _build_inserted_lines(
    right: NormalizedDocument,
    j1: int,
    j2: int,
) -> Iterable[DiffLine]:
    for right_idx in range(j1, j2):
        line_text = right.lines[right_idx]
        yield DiffLine(
            kind=ChangeType.INSERTED,
            left_lineno=None,
            right_lineno=right_idx + 1,
            left_text=None,
            right_text=line_text,
        )


def _build_replaced_lines(
    left: NormalizedDocument,
    right: NormalizedDocument,
    i1: int,
    i2: int,
    j1: int,
    j2: int,
) -> Iterable[DiffLine]:
    lines: List[DiffLine] = []
    left_span = left.lines[i1:i2]
    right_span = right.lines[j1:j2]
    pair_count = min(len(left_span), len(right_span))

    for offset in range(pair_count):
        left_idx = i1 + offset
        right_idx = j1 + offset
        left_line = left_span[offset]
        right_line = right_span[offset]
        segments = diff_inline(left_line, right_line)
        lines.append(
            DiffLine(
                kind=ChangeType.EDITED,
                left_lineno=left_idx + 1,
                right_lineno=right_idx + 1,
                left_text=left_line,
                right_text=right_line,
                segments=segments,
            )
        )

    for leftover_idx in range(i1 + pair_count, i2):
        lines.append(
            DiffLine(
                kind=ChangeType.DELETED,
                left_lineno=leftover_idx + 1,
                right_lineno=None,
                left_text=left.lines[leftover_idx],
                right_text=None,
            )
        )

    for leftover_idx in range(j1 + pair_count, j2):
        lines.append(
            DiffLine(
                kind=ChangeType.INSERTED,
                left_lineno=None,
                right_lineno=leftover_idx + 1,
                left_text=None,
                right_text=right.lines[leftover_idx],
            )
        )

    return lines
