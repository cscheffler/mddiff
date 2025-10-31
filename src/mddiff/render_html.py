"""HTML rendering utilities for Markdown diffs."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable, Literal

from .models import ChangeType, DiffLine, DiffResult, InlineDiffSegment


@dataclass(frozen=True)
class HtmlRenderOptions:
    """Tunable options for HTML diff rendering."""

    include_styles: bool = True
    class_prefix: str = "mddiff"
    show_line_numbers: bool = True
    layout: Literal["split", "unified"] = "split"


def render_html(diff_result: DiffResult, options: HtmlRenderOptions | None = None) -> str:
    """Render a diff result as annotated HTML.

    Parameters
    ----------
    diff_result:
        The diff computation output to render.
    options:
        Optional rendering tweaks. When omitted, sensible defaults are used.
    """

    opts = options or HtmlRenderOptions()
    classes = _ClassRegistry(opts.class_prefix)

    if opts.layout not in {"split", "unified"}:
        raise ValueError(f"Unsupported HTML diff layout: {opts.layout}")

    parts: list[str] = []
    if opts.include_styles:
        stylesheet = default_html_styles(classes.prefix)
        parts.append(f'<style type="text/css">{stylesheet}</style>')

    root_classes = [classes.root, classes.root_layout(opts.layout)]
    root_attrs = [f'class="{" ".join(root_classes)}"']
    if diff_result.context is not None:
        root_attrs.append(f'data-context="{diff_result.context}"')
    parts.append(f'<div {" ".join(root_attrs)}>')

    for line in diff_result.lines:
        if opts.layout == "split":
            parts.append(_render_split_line_html(line, classes, opts))
        else:
            parts.extend(_render_unified_line_html(line, classes, opts))

    parts.append('</div>')
    return "".join(parts)


def default_html_styles(class_prefix: str = "mddiff") -> str:
    """Return the default CSS used by ``render_html``.

    The stylesheet is namespace-aware: changing ``class_prefix`` lets callers
    embed multiple rendered diffs on the same page without collisions.
    """

    prefix = _normalize_prefix(class_prefix)
    return (
        f".{prefix}-diff {{\n"
        f"  font-family: var(--{prefix}-font, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace);\n"
        f"  font-size: 13px;\n"
        f"  line-height: 1.45;\n"
        f"  color: var(--{prefix}-foreground, #1f2933);\n"
        f"  background: var(--{prefix}-background, #f8f9fb);\n"
        f"  border: 1px solid var(--{prefix}-border, #d2d6dc);\n"
        f"  border-radius: 6px;\n"
        f"  overflow: auto;\n"
        f"}}\n"
        f".{prefix}-hunk {{\n"
        f"  padding: 4px 12px;\n"
        f"  background: var(--{prefix}-hunk-background, #e5edff);\n"
        f"  color: var(--{prefix}-hunk-foreground, #1e3a8a);\n"
        f"  font-weight: 600;\n"
        f"  border-bottom: 1px solid var(--{prefix}-border, #d2d6dc);\n"
        f"  white-space: pre;\n"
        f"}}\n"
        f".{prefix}-line {{\n"
        f"  display: grid;\n"
        f"  gap: 8px;\n"
        f"  padding: 2px 12px;\n"
        f"  align-items: start;\n"
        f"  border-bottom: 1px solid var(--{prefix}-divider, #eaecf0);\n"
        f"  white-space: pre-wrap;\n"
        f"  word-break: break-word;\n"
        f"}}\n"
        f".{prefix}-diff--layout-split .{prefix}-line {{\n"
        f"  grid-template-columns: minmax(3ch, auto) minmax(3ch, auto) 1fr 1fr;\n"
        f"}}\n"
        f".{prefix}-diff--layout-unified .{prefix}-line {{\n"
        f"  grid-template-columns: minmax(3ch, auto) minmax(3ch, auto) minmax(2ch, auto) 1fr;\n"
        f"}}\n"
        f".{prefix}-line:last-child {{\n"
        f"  border-bottom: none;\n"
        f"}}\n"
        f".{prefix}-line--unchanged {{\n"
        f"  background: var(--{prefix}-unchanged-background, transparent);\n"
        f"}}\n"
        f".{prefix}-line--inserted {{\n"
        f"  background: var(--{prefix}-inserted-background, #e6ffed);\n"
        f"}}\n"
        f".{prefix}-line--deleted {{\n"
        f"  background: var(--{prefix}-deleted-background, #ffeef0);\n"
        f"}}\n"
        f".{prefix}-line--edited {{\n"
        f"  background: var(--{prefix}-edited-background, #fff8e1);\n"
        f"}}\n"
        f".{prefix}-gutter {{\n"
        f"  font-variant-numeric: tabular-nums;\n"
        f"  text-align: right;\n"
        f"  color: var(--{prefix}-gutter-foreground, #6b7280);\n"
        f"  min-width: 3ch;\n"
        f"}}\n"
        f".{prefix}-gutter--hidden {{\n"
        f"  visibility: hidden;\n"
        f"}}\n"
        f".{prefix}-gutter--empty::before {{\n"
        f"  content: '\\00a0';\n"
        f"}}\n"
        f".{prefix}-content {{\n"
        f"  white-space: inherit;\n"
        f"}}\n"
        f".{prefix}-content--left, .{prefix}-content--right {{\n"
        f"  white-space: inherit;\n"
        f"}}\n"
        f".{prefix}-content--unified {{\n"
        f"  white-space: inherit;\n"
        f"}}\n"
        f".{prefix}-content--empty {{\n"
        f"  color: var(--{prefix}-empty-foreground, #9ca3af);\n"
        f"}}\n"
        f".{prefix}-segment {{\n"
        f"  white-space: inherit;\n"
        f"}}\n"
        f".{prefix}-segment--unchanged {{\n"
        f"  background: transparent;\n"
        f"  color: inherit;\n"
        f"}}\n"
        f".{prefix}-segment--inserted {{\n"
        f"  background: var(--{prefix}-segment-inserted, #bbf7d0);\n"
        f"  color: var(--{prefix}-segment-inserted-foreground, #065f46);\n"
        f"}}\n"
        f".{prefix}-segment--deleted {{\n"
        f"  background: var(--{prefix}-segment-deleted, #fecdd3);\n"
        f"  color: var(--{prefix}-segment-deleted-foreground, #9f1239);\n"
        f"  text-decoration-line: line-through;\n"
        f"  text-decoration-thickness: 2px;\n"
        f"  text-decoration-color: currentColor;\n"
        f"}}\n"
        f".{prefix}-segment--edited {{\n"
        f"  background: var(--{prefix}-segment-edited, #fde68a);\n"
        f"  color: var(--{prefix}-segment-edited-foreground, #92400e);\n"
        f"}}\n"
        f".{prefix}-segment--side-left {{\n"
        f"  white-space: inherit;\n"
        f"}}\n"
        f".{prefix}-segment--side-right {{\n"
        f"  white-space: inherit;\n"
        f"}}\n"
        f".{prefix}-line--skipped {{\n"
        f"  background: var(--{prefix}-skipped-background, #f3f4f6);\n"
        f"  color: var(--{prefix}-skipped-foreground, #4b5563);\n"
        f"}}\n"
    )


def _render_split_line_html(line: DiffLine, classes: _ClassRegistry, opts: HtmlRenderOptions) -> str:
    if line.kind is ChangeType.SKIPPED:
        text = (line.left_text or line.right_text or "").rstrip("\n")
        hunk = escape(text)
        left = "" if line.left_lineno is None else line.left_lineno
        right = "" if line.right_lineno is None else line.right_lineno
        return (
            f'<div class="{classes.hunk}" data-change-kind="skipped" '
            f'data-left-start="{left}" data-right-start="{right}">{hunk}</div>'
        )

    line_classes = [classes.line, classes.line_kind(line.kind)]
    attrs = [f'class="{" ".join(line_classes)}"', f'data-change-kind="{line.kind.value}"']
    if line.left_lineno is not None:
        attrs.append(f'data-left-lineno="{line.left_lineno}"')
    if line.right_lineno is not None:
        attrs.append(f'data-right-lineno="{line.right_lineno}"')

    gutters = ""
    if opts.show_line_numbers:
        gutters = (
            _render_gutter(line.left_lineno, "left", classes) +
            _render_gutter(line.right_lineno, "right", classes)
        )
    else:
        gutters = (
            _render_gutter(None, "left", classes, hidden=True) +
            _render_gutter(None, "right", classes, hidden=True)
        )

    left_content = _render_side_content(line, "left", classes)
    right_content = _render_side_content(line, "right", classes)

    return (
        f'<div {" ".join(attrs)}>'
        f'{gutters}'
        f'{left_content}'
        f'{right_content}'
        f'</div>'
    )


def _render_unified_line_html(
    line: DiffLine, classes: _ClassRegistry, opts: HtmlRenderOptions
) -> tuple[str, ...]:
    if line.kind is ChangeType.SKIPPED:
        text = (line.left_text or line.right_text or "").rstrip("\n")
        hunk = escape(text)
        left = "" if line.left_lineno is None else line.left_lineno
        right = "" if line.right_lineno is None else line.right_lineno
        return (
            f'<div class="{classes.hunk}" data-change-kind="skipped" '
            f'data-left-start="{left}" data-right-start="{right}">{hunk}</div>',
        )

    if line.kind is ChangeType.EDITED:
        combined_entry = _render_unified_entry(
            line,
            classes,
            opts,
            entry_kind=ChangeType.EDITED,
            marker_char="",
            side=None,
            left_lineno=line.left_lineno,
            right_lineno=line.right_lineno,
        )
        return (combined_entry,)

    entry_kind = line.kind
    marker_char = {
        ChangeType.UNCHANGED: "",
        ChangeType.INSERTED: "",
        ChangeType.DELETED: "",
    }.get(entry_kind, "")

    return (
        _render_unified_entry(
            line,
            classes,
            opts,
            entry_kind=entry_kind,
            marker_char=marker_char,
            side="right" if entry_kind is ChangeType.INSERTED else "left",
            left_lineno=line.left_lineno,
            right_lineno=line.right_lineno,
        ),
    )


def _render_unified_entry(
    line: DiffLine,
    classes: _ClassRegistry,
    opts: HtmlRenderOptions,
    *,
    entry_kind: ChangeType,
    marker_char: str,
    side: str | None,
    left_lineno: int | None,
    right_lineno: int | None,
) -> str:
    line_classes = [classes.line, classes.line_kind(entry_kind)]
    attrs = [f'class="{" ".join(line_classes)}"', f'data-change-kind="{entry_kind.value}"']
    if left_lineno is not None:
        attrs.append(f'data-left-lineno="{left_lineno}"')
    if right_lineno is not None:
        attrs.append(f'data-right-lineno="{right_lineno}"')

    if opts.show_line_numbers:
        gutters = (
            _render_gutter(left_lineno, "left", classes)
            + _render_gutter(right_lineno, "right", classes)
        )
    else:
        gutters = (
            _render_gutter(None, "left", classes, hidden=True)
            + _render_gutter(None, "right", classes, hidden=True)
        )

    content_html = _render_unified_content(line, entry_kind, side, classes)
    has_content = bool(content_html.strip())
    content_classes = [classes.content, classes.content_unified]
    if not has_content:
        content_classes.append(classes.content_empty)
    content_span = f'<span class="{" ".join(content_classes)}">{content_html}</span>'

    return (
        f'<div {" ".join(attrs)}>'
        f'{gutters}'
        f'{content_span}'
        f'</div>'
    )


def _render_unified_content(
    line: DiffLine,
    entry_kind: ChangeType,
    side: str | None,
    classes: _ClassRegistry,
) -> str:
    if entry_kind is ChangeType.EDITED:
        return _render_combined_segments(line, classes)

    if line.kind is ChangeType.EDITED and side in {"left", "right"}:
        return _render_inline_segments(line, side, classes, include_newline=False)

    if entry_kind is ChangeType.DELETED:
        return escape(_normalize_unified_text(line.left_text or ""))
    if entry_kind is ChangeType.INSERTED:
        return escape(_normalize_unified_text(line.right_text or ""))
    # unchanged fallback
    text = line.right_text or line.left_text or ""
    return escape(_normalize_unified_text(text))


def _render_side_content(line: DiffLine, side: str, classes: _ClassRegistry) -> str:
    has_content = False
    if line.kind is ChangeType.EDITED:
        rendered = _render_inline_segments(line, side, classes)
        if not rendered:
            text = _extract_text(line, side)
            rendered = escape(text) if text else ""
        has_content = bool(rendered)
    else:
        text = _extract_text(line, side)
        rendered = escape(text) if text else ""
        has_content = bool(text)

    content_classes = [classes.content, classes.content_side(side)]
    if not has_content:
        content_classes.append(classes.content_empty)
    return f'<span class="{" ".join(content_classes)}">{rendered}</span>'


def _render_inline_segments(
    line: DiffLine,
    side: str,
    classes: _ClassRegistry,
    *,
    include_newline: bool = True,
) -> str:
    segments: Iterable[InlineDiffSegment] = line.segments
    pieces: list[str] = []
    for segment in segments:
        text = _segment_text(segment, side)
        if text is None:
            continue
        if not include_newline and text == "\n":
            continue
        if not include_newline and text.endswith("\n"):
            text = text.rstrip("\n")
            if not text:
                continue
        segment_classes = [classes.segment]
        segment_classes.append(classes.segment_kind(_segment_display_kind(segment, side)))
        segment_classes.append(classes.segment_side(side))
        pieces.append(f'<span class="{" ".join(segment_classes)}">{escape(text)}</span>')
    return "".join(pieces)


def _segment_display_kind(segment: InlineDiffSegment, side: str) -> ChangeType:
    if segment.kind is ChangeType.EDITED:
        return ChangeType.DELETED if side == "left" else ChangeType.INSERTED
    return segment.kind


def _segment_text(segment: InlineDiffSegment, side: str) -> str | None:
    if side == "left":
        if segment.kind is ChangeType.INSERTED:
            return None
        return segment.left_text
    if segment.kind is ChangeType.DELETED:
        return None
    return segment.right_text


def _extract_text(line: DiffLine, side: str) -> str:
    if side == "left":
        return line.left_text or ""
    return line.right_text or ""


def _render_combined_segments(line: DiffLine, classes: _ClassRegistry) -> str:
    pieces: list[str] = []
    for segment in line.segments:
        if segment.kind is ChangeType.UNCHANGED:
            text = segment.right_text or segment.left_text or ""
            cleaned = _normalize_unified_text(text)
            if not cleaned:
                continue
            segment_classes = [classes.segment, classes.segment_kind(ChangeType.UNCHANGED)]
            pieces.append(f'<span class="{" ".join(segment_classes)}">{escape(cleaned)}</span>')
        elif segment.kind is ChangeType.INSERTED:
            text = _normalize_unified_text(segment.right_text)
            if not text:
                continue
            segment_classes = [classes.segment, classes.segment_kind(ChangeType.INSERTED), classes.segment_side("right")]
            pieces.append(f'<span class="{" ".join(segment_classes)}">{escape(text)}</span>')
        elif segment.kind is ChangeType.DELETED:
            text = _normalize_unified_text(segment.left_text)
            if not text:
                continue
            segment_classes = [classes.segment, classes.segment_kind(ChangeType.DELETED), classes.segment_side("left")]
            pieces.append(f'<span class="{" ".join(segment_classes)}">{escape(text)}</span>')
        elif segment.kind is ChangeType.EDITED:
            left_text = _normalize_unified_text(segment.left_text)
            right_text = _normalize_unified_text(segment.right_text)
            if left_text:
                segment_classes = [classes.segment, classes.segment_kind(ChangeType.DELETED), classes.segment_side("left")]
                pieces.append(f'<span class="{" ".join(segment_classes)}">{escape(left_text)}</span>')
            if right_text:
                segment_classes = [classes.segment, classes.segment_kind(ChangeType.INSERTED), classes.segment_side("right")]
                pieces.append(f'<span class="{" ".join(segment_classes)}">{escape(right_text)}</span>')
    return "".join(pieces)


def _normalize_unified_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("\n", "")


def _render_gutter(
    value: int | None,
    side: str,
    classes: _ClassRegistry,
    *,
    hidden: bool = False,
) -> str:
    display = "" if value is None else str(value)
    gutter_classes = [classes.gutter, classes.gutter_side(side)]
    if hidden:
        gutter_classes.append(classes.gutter_hidden)
    if not display:
        gutter_classes.append(classes.gutter_empty)
    escaped = escape(display)
    data_attr = f' data-lineno="{display}"' if display else ""
    return f'<span class="{" ".join(gutter_classes)}"{data_attr}>{escaped}</span>'


class _ClassRegistry:
    """Helper for constructing namespaced CSS classes."""

    def __init__(self, prefix: str) -> None:
        self.prefix = _normalize_prefix(prefix)
        self.root = f"{self.prefix}-diff"
        self.hunk = f"{self.prefix}-hunk"
        self.line = f"{self.prefix}-line"
        self.segment = f"{self.prefix}-segment"
        self.gutter = f"{self.prefix}-gutter"
        self.content = f"{self.prefix}-content"
        self.content_empty = f"{self.prefix}-content--empty"
        self.content_unified = f"{self.prefix}-content--unified"
        self.gutter_empty = f"{self.prefix}-gutter--empty"
        self.gutter_hidden = f"{self.prefix}-gutter--hidden"

    def line_kind(self, kind: ChangeType) -> str:
        return f"{self.prefix}-line--{kind.value}"

    def root_layout(self, layout: str) -> str:
        return f"{self.prefix}-diff--layout-{layout}"

    def gutter_side(self, side: str) -> str:
        return f"{self.prefix}-gutter--{side}"

    def content_side(self, side: str) -> str:
        return f"{self.prefix}-content--{side}"

    def segment_kind(self, kind: ChangeType) -> str:
        return f"{self.prefix}-segment--{kind.value}"

    def segment_side(self, side: str) -> str:
        return f"{self.prefix}-segment--side-{side}"


def _normalize_prefix(prefix: str) -> str:
    cleaned = (prefix or "mddiff").strip()
    if not cleaned:
        cleaned = "mddiff"
    sanitized = ''.join(ch for ch in cleaned if ch.isalnum() or ch in "-_")
    if not sanitized:
        return "mddiff"
    return sanitized
