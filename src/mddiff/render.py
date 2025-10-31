"""Rendering helpers for presenting diff results."""

from __future__ import annotations

from typing import Iterable, List

from .models import ChangeType, DiffLine, DiffResult, InlineDiffSegment


def render_unified(diff_result: DiffResult) -> str:
    """Render a :class:`DiffResult` as traditional unified diff text.

    Parameters
    ----------
    diff_result:
        Structured diff output produced by :func:`mddiff.diff` or
        :func:`mddiff.diff_normalized`.

    Returns
    -------
    str
        Unified diff text with inline `{+ +}` / `[- -]` markers for edited
        spans.
    """

    rendered_lines: List[str] = []

    for line in diff_result.lines:
        if line.kind is ChangeType.UNCHANGED:
            rendered_lines.append(f" {line.right_text or line.left_text or ''}")
        elif line.kind is ChangeType.DELETED:
            rendered_lines.append(f"-{line.left_text or ''}")
        elif line.kind is ChangeType.INSERTED:
            rendered_lines.append(f"+{line.right_text or ''}")
        elif line.kind is ChangeType.EDITED:
            rendered_lines.extend(_render_edited_line(line))
        elif line.kind is ChangeType.SKIPPED:
            rendered_lines.append(line.left_text or line.right_text or "")
        else:  # pragma: no cover - defensive guard
            raise ValueError(f"Unsupported line kind: {line.kind}")

    return "".join(rendered_lines)


def _render_edited_line(line: DiffLine) -> Iterable[str]:
    """Render the left/right components for an edited line."""
    left_text = _render_inline_segments(line, side="left")
    right_text = _render_inline_segments(line, side="right")
    output: List[str] = []

    if left_text is not None:
        output.append(f"-{left_text}")
    if right_text is not None:
        output.append(f"+{right_text}")
    return output


def _render_inline_segments(line: DiffLine, *, side: str) -> str | None:
    """Render inline segments for one side of an edited line."""
    assert line.kind is ChangeType.EDITED

    segments = line.segments
    if not segments:
        # Fallback to the raw line text if no segments were captured.
        raw = line.left_text if side == "left" else line.right_text
        return raw or ""

    pieces: List[str] = []
    for segment in segments:
        pieces.append(_render_segment(segment, side=side))

    rendered = "".join(filter(None, pieces))
    source = line.left_text if side == "left" else line.right_text
    if source and source.endswith("\n") and not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def _render_segment(segment: InlineDiffSegment, *, side: str) -> str:
    """Render a single inline segment for the requested side."""
    if segment.kind is ChangeType.UNCHANGED:
        return segment.left_text if side == "left" else segment.right_text
    if segment.kind is ChangeType.DELETED:
        return f"[-{segment.left_text}-]" if side == "left" else ""
    if segment.kind is ChangeType.INSERTED:
        return f"{{+{segment.right_text}+}}" if side == "right" else ""
    if segment.kind is ChangeType.EDITED:
        if side == "left":
            return f"[-{segment.left_text}-]" if segment.left_text else ""
        return f"{{+{segment.right_text}+}}" if segment.right_text else ""
    raise ValueError(f"Unsupported segment kind: {segment.kind}")
