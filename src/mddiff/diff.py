"""Line-level diff engine for normalized Markdown documents."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable, List, Sequence, Tuple

from .inline import diff_inline
from .models import ChangeType, DiffLine, DiffResult, InlineDiffConfig, NormalizedDocument
from .normalize import normalize


def diff(
    left: str | NormalizedDocument,
    right: str | NormalizedDocument,
    *,
    left_id: str = "left",
    right_id: str = "right",
    inline_config: InlineDiffConfig | None = None,
    context: int | None = None,
) -> DiffResult:
    """Normalize inputs as needed and compute a unified diff."""

    left_doc = left if isinstance(left, NormalizedDocument) else normalize(left, source_id=left_id)
    right_doc = right if isinstance(right, NormalizedDocument) else normalize(right, source_id=right_id)
    return diff_normalized(
        left_doc,
        right_doc,
        inline_config=inline_config,
        context=context,
    )


def diff_normalized(
    left: NormalizedDocument,
    right: NormalizedDocument,
    *,
    inline_config: InlineDiffConfig | None = None,
    context: int | None = None,
) -> DiffResult:
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
                _build_replaced_lines(left, right, i1, i2, j1, j2, inline_config)
            )
        else:  # pragma: no cover - defensive guard
            raise ValueError(f"Unexpected opcode: {tag}")

    filtered_lines = _apply_context(lines, context)
    return DiffResult(left=left, right=right, lines=filtered_lines, context=context)


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
    inline_config: InlineDiffConfig | None,
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
        if not _should_inline(left_line, right_line, inline_config):
            lines.append(
                DiffLine(
                    kind=ChangeType.DELETED,
                    left_lineno=left_idx + 1,
                    right_lineno=None,
                    left_text=left_line,
                    right_text=None,
                )
            )
            lines.append(
                DiffLine(
                    kind=ChangeType.INSERTED,
                    left_lineno=None,
                    right_lineno=right_idx + 1,
                    left_text=None,
                    right_text=right_line,
                )
            )
        else:
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


def _should_inline(
    left_line: str,
    right_line: str,
    inline_config: InlineDiffConfig | None,
) -> bool:
    left_body = left_line.rstrip("\n")
    right_body = right_line.rstrip("\n")
    if not left_body and not right_body:
        return True

    matcher = SequenceMatcher(None, left_body, right_body, autojunk=False)
    config = inline_config or InlineDiffConfig()
    if matcher.real_quick_ratio() < config.min_real_quick_ratio:
        return False
    if matcher.quick_ratio() < config.min_quick_ratio:
        return False
    return matcher.ratio() >= config.min_ratio


def _apply_context(lines: List[DiffLine], context: int | None) -> Tuple[DiffLine, ...]:
    if context is None:
        return tuple(lines)
    if context < 0:
        raise ValueError("context must be non-negative")
    if not lines:
        return tuple()

    change_indices = [idx for idx, line in enumerate(lines) if line.kind is not ChangeType.UNCHANGED]
    if not change_indices:
        return tuple()

    keep = [False] * len(lines)
    for idx in change_indices:
        keep[idx] = True
        if context > 0:
            start = max(0, idx - context)
            end = min(len(lines), idx + context + 1)
            for j in range(start, end):
                if lines[j].kind is ChangeType.UNCHANGED:
                    keep[j] = True

    kept_indices = [idx for idx, flag in enumerate(keep) if flag]
    if not kept_indices:
        return tuple()

    blocks: List[Tuple[int, int]] = []
    current_start = kept_indices[0]
    current_end = kept_indices[0]
    for idx in kept_indices[1:]:
        if idx == current_end + 1:
            current_end = idx
        else:
            blocks.append((current_start, current_end))
            current_start = current_end = idx
    blocks.append((current_start, current_end))

    filtered: List[DiffLine] = []
    prev_left = 0
    prev_right = 0

    for start, end in blocks:
        header = _make_hunk_header(lines, start, end, prev_left, prev_right)
        if header is not None:
            filtered.append(header)
        block_lines = lines[start : end + 1]
        filtered.extend(block_lines)

        left_candidates = [line.left_lineno for line in block_lines if line.left_lineno is not None]
        right_candidates = [line.right_lineno for line in block_lines if line.right_lineno is not None]
        if left_candidates:
            prev_left = left_candidates[-1]
        if right_candidates:
            prev_right = right_candidates[-1]

    return tuple(filtered)


def _make_hunk_header(
    lines: Sequence[DiffLine],
    start: int,
    end: int,
    prev_left: int,
    prev_right: int,
) -> DiffLine | None:
    block = lines[start : end + 1]
    left_numbers = [line.left_lineno for line in block if line.left_lineno is not None]
    right_numbers = [line.right_lineno for line in block if line.right_lineno is not None]

    left_start = left_numbers[0] if left_numbers else prev_left + 1
    right_start = right_numbers[0] if right_numbers else prev_right + 1

    left_len = len(left_numbers)
    right_len = len(right_numbers)

    header_text = f"@@ -{left_start},{left_len} +{right_start},{right_len} @@\n"
    return DiffLine(
        kind=ChangeType.SKIPPED,
        left_lineno=left_start,
        right_lineno=right_start,
        left_text=header_text,
        right_text=header_text,
    )
