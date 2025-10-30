"""Inline diff utilities for Markdown lines."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Iterable, List, Sequence

from .models import ChangeType, InlineDiffSegment

_TOKEN_RE = re.compile(r"\s+|[A-Za-z0-9_]+|[^\w\s]")


def diff_inline(left: str, right: str) -> tuple[InlineDiffSegment, ...]:
    """Compute inline diff segments between two lines of text."""

    left_body, left_newline = _strip_trailing_newline(left)
    right_body, right_newline = _strip_trailing_newline(right)

    left_tokens = _tokenize(left_body)
    right_tokens = _tokenize(right_body)

    matcher = SequenceMatcher(None, left_tokens, right_tokens, autojunk=False)
    segments: List[InlineDiffSegment] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        left_text = "".join(left_tokens[i1:i2])
        right_text = "".join(right_tokens[j1:j2])

        if tag == "equal":
            if left_text:
                segments.append(_segment(ChangeType.UNCHANGED, left_text, right_text))
        elif tag == "delete":
            if left_text:
                segments.append(_segment(ChangeType.DELETED, left_text, ""))
        elif tag == "insert":
            if right_text:
                segments.append(_segment(ChangeType.INSERTED, "", right_text))
        elif tag == "replace":
            if left_text or right_text:
                segments.append(_segment(ChangeType.EDITED, left_text, right_text))
        else:  # pragma: no cover - defensive guard
            raise ValueError(f"Unknown opcode: {tag}")

    if left_newline or right_newline:
        # Preserve the trailing newline so renderers can round-trip it.
        newline_segment = _segment(
            ChangeType.UNCHANGED
            if left_newline and right_newline
            else (ChangeType.DELETED if left_newline else ChangeType.INSERTED),
            "\n" if left_newline else "",
            "\n" if right_newline else "",
        )
        segments.append(newline_segment)

    segments = _coalesce_segments(segments)
    segments = _merge_whitespace_bridges(segments)
    return segments


def _segment(kind: ChangeType, left: str, right: str) -> InlineDiffSegment:
    return InlineDiffSegment(kind=kind, left_text=left, right_text=right)


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return _TOKEN_RE.findall(text)


def _strip_trailing_newline(value: str) -> tuple[str, bool]:
    if value.endswith("\n"):
        return value[:-1], True
    return value, False


def _coalesce_segments(segments: Sequence[InlineDiffSegment]) -> tuple[InlineDiffSegment, ...]:
    if not segments:
        return ()

    coalesced: List[InlineDiffSegment] = [segments[0]]
    for segment in segments[1:]:
        previous = coalesced[-1]
        if segment.kind is previous.kind:
            merged = _segment(
                segment.kind,
                previous.left_text + segment.left_text,
                previous.right_text + segment.right_text,
            )
            coalesced[-1] = merged
        else:
            coalesced.append(segment)
    return tuple(coalesced)


def _merge_whitespace_bridges(
    segments: Sequence[InlineDiffSegment],
) -> tuple[InlineDiffSegment, ...]:
    if len(segments) < 3:
        return tuple(segments)

    result: List[InlineDiffSegment] = []
    i = 0
    while i < len(segments):
        segment = segments[i]
        if (
            0 < i < len(segments) - 1
            and segment.kind is ChangeType.UNCHANGED
            and _is_mergeable_whitespace(segment)
            and _is_change_segment(result[-1])
            and _is_change_segment(segments[i + 1])
        ):
            prev = result.pop()
            next_segment = segments[i + 1]
            combined = _combine_segments(prev, segment, next_segment)
            result.append(combined)
            i += 2
            continue

        result.append(segment)
        i += 1

    return tuple(result)


def _is_mergeable_whitespace(segment: InlineDiffSegment) -> bool:
    text = segment.left_text or segment.right_text
    if not text:
        return False
    if "\n" in text:
        return False
    return text.strip() == ""


def _is_change_segment(segment: InlineDiffSegment) -> bool:
    return segment.kind in {ChangeType.EDITED, ChangeType.INSERTED, ChangeType.DELETED}


def _combine_segments(
    left_segment: InlineDiffSegment,
    whitespace: InlineDiffSegment,
    right_segment: InlineDiffSegment,
) -> InlineDiffSegment:
    left_text = left_segment.left_text + whitespace.left_text + right_segment.left_text
    right_text = left_segment.right_text + whitespace.right_text + right_segment.right_text
    has_left = bool(left_text)
    has_right = bool(right_text)

    if has_left and has_right:
        kind = ChangeType.EDITED
    elif has_left:
        kind = ChangeType.DELETED
    else:
        kind = ChangeType.INSERTED

    return InlineDiffSegment(kind=kind, left_text=left_text, right_text=right_text)
