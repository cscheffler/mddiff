from __future__ import annotations

from collections import Counter
import hashlib
import io
import math
import re
from typing import IO

from .models import NormalizationMetadata, NormalizedDocument

UNORDERED_LIST_RE = re.compile(r"^([ \t]*)([*+-])\s+(.*)$")
ORDERED_LIST_RE = re.compile(r"^([ \t]*)\d+[.)]\s+(.*)$")
HORIZONTAL_RULE_COMPACT_RE = re.compile(r"^[*\-_]{3,}$")
FENCE_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})(.*)$")
SETEXT_UNDERLINE_RE = re.compile(r"^ {0,3}(=+|-+)\s*$")
INLINE_CODE_RE = re.compile(r"`+[^`]+?`+")
STRONG_UNDERSCORE_RE = re.compile(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)")
EMPHASIS_UNDERSCORE_RE = re.compile(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?[-]+:?\s*(\|\s*:?[-]+:?\s*)+\|?\s*$")
ATX_HEADING_RE = re.compile(r"^(?P<marker>#{1,6})(?P<body>\s.*)?$")


def normalize(
    value: str | bytes | IO[str] | IO[bytes], *, source_id: str = "unknown"
) -> NormalizedDocument:
    """Normalize Markdown text into a deterministic representation.

    Parameters
    ----------
    value:
        Markdown content as text, bytes, or a readable stream. Bytes are
        decoded as UTF-8.
    source_id:
        Identifier recorded on the resulting :class:`NormalizedDocument`
        (defaults to ``"unknown"``).

    Returns
    -------
    NormalizedDocument
        Canonical Markdown with line-level metadata, transformation counters,
        and a stable SHA-256 digest.
    """

    original_text = _coerce_text(value)
    original_text = _normalize_line_endings(original_text)
    original_text = _strip_bom(original_text)

    normalized_text, stats = _normalize_blocks(original_text)
    normalized_text = _trim_blank_ends(normalized_text)
    normalized_text = _ensure_trailing_newline(normalized_text)

    lines = tuple(normalized_text.splitlines(keepends=True))
    metadata = NormalizationMetadata(
        original_length=len(original_text),
        normalized_length=len(normalized_text),
        transformations=dict(stats),
    )
    digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return NormalizedDocument(
        source_id=source_id,
        lines=lines,
        metadata=metadata,
        digest=digest,
    )


def _coerce_text(value: str | bytes | IO[str] | IO[bytes]) -> str:
    """Coerce supported input representations into a Unicode string."""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, io.TextIOBase):
        return value.read()
    if isinstance(value, io.BufferedIOBase):
        return value.read().decode("utf-8")
    if hasattr(value, "read"):
        data = value.read()
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return str(data)
    raise TypeError(f"Unsupported input type: {type(value)!r}")


def _normalize_line_endings(text: str) -> str:
    """Standardize carriage returns to single LF characters."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_bom(text: str) -> str:
    """Remove a UTF-8 BOM prefix if present."""
    return text.lstrip("\ufeff")


def _trim_blank_ends(text: str) -> str:
    """Trim leading and trailing blank lines."""
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines)


def _ensure_trailing_newline(text: str) -> str:
    """Ensure the text terminates with a newline."""
    return text if text.endswith("\n") else text + "\n"


def _normalize_blocks(text: str) -> tuple[str, Counter[str]]:
    """Apply block-level normalization to the document."""
    stats: Counter[str] = Counter()
    lines = text.splitlines()
    i = 0
    output: list[str] = []

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            if output and output[-1] != "":
                output.append("")
            i += 1
            continue

        fence_match = _match_fence_start(line)
        if fence_match:
            block_lines, consumed, changed = _normalize_code_fence(lines, i, fence_match)
            output.extend(block_lines)
            if changed:
                stats["code_fence_marker"] += changed
            i += consumed
            continue

        if _is_setext_heading(lines, i):
            heading_line = _normalize_setext_heading(lines[i], lines[i + 1])
            output.append(heading_line)
            stats["setext_to_atx"] += 1
            i += 2
            continue

        stripped = line.strip()
        if _looks_like_horizontal_rule(stripped):
            if stripped != "---":
                stats["horizontal_rule"] += 1
            output.append("---")
            i += 1
            continue

        heading_match = ATX_HEADING_RE.match(line.strip())
        if heading_match:
            output.append(_normalize_atx_heading(line))
            i += 1
            continue

        if _is_table_block_start(lines, i):
            block, consumed, table_stats = _normalize_table_block(lines, i)
            output.extend(block)
            stats.update(table_stats)
            i += consumed
            continue

        if _is_blockquote_line(line):
            block, consumed, block_stats = _normalize_blockquote_block(lines, i)
            output.extend(block)
            stats.update(block_stats)
            i += consumed
            continue

        if _is_list_item_line(line):
            block, consumed, list_stats = _normalize_list_block(lines, i)
            output.extend(block)
            stats.update(list_stats)
            i += consumed
            continue

        paragraph_lines: list[str] = []
        while i < len(lines):
            current = lines[i]
            if not current.strip():
                break
            if _is_block_start(lines, i):
                break
            paragraph_lines.append(current.rstrip())
            i += 1
        if paragraph_lines:
            paragraph = _collapse_spaces(" ".join(paragraph_lines))
            paragraph = _normalize_inline_markup(paragraph)
            output.append(paragraph)
        continue

    cleaned = _squash_blank_lines(output)
    return "\n".join(cleaned), stats


def _looks_like_horizontal_rule(stripped: str) -> bool:
    """Return True when the stripped line resembles a horizontal rule."""
    compact = stripped.replace(" ", "")
    return bool(compact) and HORIZONTAL_RULE_COMPACT_RE.fullmatch(compact)


def _is_blockquote_line(line: str) -> bool:
    """Return True when the line begins a blockquote."""
    stripped = line.lstrip()
    if not stripped.startswith(">"):
        return False
    non_marker_idx = 0
    while non_marker_idx < len(stripped) and stripped[non_marker_idx] in "> \t":
        non_marker_idx += 1
    return non_marker_idx > 0


def _match_fence_start(line: str) -> re.Match[str] | None:
    """Match a potential fenced code block marker."""
    stripped = line.lstrip()
    return FENCE_RE.match(stripped)


def _normalize_code_fence(lines: list[str], start: int, match: re.Match[str]) -> tuple[list[str], int, int]:
    """Normalize fenced code block markers and capture their body."""
    marker = match.group(2)
    language = match.group(3).strip()
    normalized_marker = "```"
    normalized_line = normalized_marker
    if language:
        normalized_line += f" {language}"
    changed = 1 if marker != normalized_marker else 0
    block = [normalized_line]
    i = start + 1
    marker_char = marker[0]
    while i < len(lines):
        current = lines[i]
        closing_match = _match_fence_start(current)
        if closing_match and closing_match.group(2)[0] == marker_char and set(closing_match.group(2)) == {marker_char}:
            block.append(normalized_marker)
            if closing_match.group(2) != normalized_marker:
                changed += 1
            return block, i - start + 1, changed
        block.append(current.rstrip("\n"))
        i += 1
    # Unterminated fence; close it ourselves
    block.append(normalized_marker)
    return block, i - start + 1, changed + 1


def _is_setext_heading(lines: list[str], index: int) -> bool:
    """Detect whether the current line pair forms a setext heading."""
    if index + 1 >= len(lines):
        return False
    return bool(lines[index].strip() and SETEXT_UNDERLINE_RE.match(lines[index + 1]))


def _normalize_setext_heading(title_line: str, underline_line: str) -> str:
    """Convert a setext heading into canonical ATX form."""
    level = 1 if underline_line.strip().startswith("=") else 2
    text = _collapse_spaces(title_line.strip())
    return f"{'#' * level} {text}".rstrip()


def _normalize_blockquote_block(lines: list[str], start: int) -> tuple[list[str], int, Counter[str]]:
    """Normalize a contiguous blockquote region."""
    raw_lines: list[str] = []
    i = start
    while i < len(lines) and _is_blockquote_line(lines[i]):
        raw_lines.append(lines[i])
        i += 1

    inner_lines = [_strip_one_blockquote_marker(line) for line in raw_lines]
    inner_text, inner_stats = _normalize_blocks("\n".join(inner_lines)) if inner_lines else ("", Counter())
    block_stats = Counter(inner_stats)

    normalized_block: list[str] = []
    if inner_text:
        for inner_line in inner_text.split("\n"):
            if inner_line.startswith(">"):
                normalized_block.append(">" + inner_line)
            elif inner_line:
                normalized_block.append(f"> {inner_line}")
            else:
                normalized_block.append(">")
    else:
        normalized_block.append(">")

    differences = _count_line_differences(raw_lines, normalized_block)
    if differences:
        block_stats["blockquote_prefix"] += differences

    return normalized_block, len(raw_lines), block_stats


def _strip_one_blockquote_marker(line: str) -> str:
    """Strip a single level of blockquote markup from a line."""
    stripped = line.lstrip()
    if not stripped.startswith(">"):
        return stripped
    stripped = stripped[1:]
    return stripped.lstrip()


def _count_line_differences(original: list[str], updated: list[str]) -> int:
    """Count differing lines between original and normalized text."""
    max_len = max(len(original), len(updated))
    diff = 0
    for idx in range(max_len):
        orig = original[idx].strip() if idx < len(original) else ""
        new = updated[idx].strip() if idx < len(updated) else ""
        if orig != new:
            diff += 1
    return diff


def _normalize_list_block(lines: list[str], start: int) -> tuple[list[str], int, Counter[str]]:
    """Normalize list markers and indentation for a list block."""
    block: list[str] = []
    stats: Counter[str] = Counter()
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            break
        unordered = UNORDERED_LIST_RE.match(line)
        ordered = ORDERED_LIST_RE.match(line)
        if not (unordered or ordered):
            break
        if unordered:
            indent, _marker, rest = unordered.groups()
            normalized_indent = " " * (_indent_depth(indent) * 4)
            rest = _normalize_inline_markup(rest.lstrip())
            normalized = f"{normalized_indent}- {rest}" if rest else f"{normalized_indent}-"
            if normalized != line.rstrip():
                stats["unordered_list_marker"] += 1
            block.append(normalized)
        else:
            indent, rest = ordered.groups()
            normalized_indent = " " * (_indent_depth(indent) * 4)
            rest = _normalize_inline_markup(rest.lstrip())
            normalized = f"{normalized_indent}1. {rest}" if rest else f"{normalized_indent}1."
            if normalized != line.rstrip():
                stats["ordered_list_marker"] += 1
            block.append(normalized)
        i += 1
    return block, i - start, stats


def _indent_depth(indent: str) -> int:
    """Compute the logical indent depth from leading whitespace."""
    expanded = indent.replace("\t", "    ")
    if not expanded:
        return 0
    if set(expanded) <= {" "} and len(expanded) % 4 == 0:
        return len(expanded) // 4
    return max(1, math.ceil(len(expanded) / 2))


def _is_block_start(lines: list[str], index: int) -> bool:
    """Return True when the line begins a new structural block."""
    line = lines[index]
    if _match_fence_start(line):
        return True
    if _is_blockquote_line(line):
        return True
    if _is_list_item_line(line):
        return True
    stripped = line.strip()
    if ATX_HEADING_RE.match(stripped):
        return True
    if _looks_like_horizontal_rule(stripped):
        return True
    if _is_setext_heading(lines, index):
        return True
    return False


def _is_list_item_line(line: str) -> bool:
    """Return True when the line represents a list item."""
    return bool(UNORDERED_LIST_RE.match(line) or ORDERED_LIST_RE.match(line))


def _collapse_spaces(text: str) -> str:
    """Collapse runs of whitespace into single spaces."""
    return re.sub(r"[ \t]+", " ", text).strip()


def _squash_blank_lines(lines: list[str]) -> list[str]:
    """Reduce multiple blank lines to at most one."""
    result: list[str] = []
    for line in lines:
        if line:
            result.append(line)
            continue
        if result and result[-1] == "":
            continue
        result.append("")
    while result and result[-1] == "":
        result.pop()
    return result


def _normalize_inline_markup(text: str) -> str:
    """Canonicalize inline emphasis while respecting escapes."""
    if not text or "_" not in text:
        return text

    placeholders: dict[str, str] = {}

    def _stash_code(match: re.Match[str]) -> str:
        token = f"@@CODE{len(placeholders)}@@"
        placeholders[token] = match.group(0)
        return token

    temp = INLINE_CODE_RE.sub(_stash_code, text)
    def strong_repl(match: re.Match[str]) -> str:
        if match.group(0) and match.group(0).startswith("\\"):  # pragma: no cover - defensive
            return match.group(0)
        return f"**{match.group(1)}**"

    def emphasis_repl(match: re.Match[str]) -> str:
        if match.group(0) and match.group(0).startswith("\\"):  # pragma: no cover - defensive
            return match.group(0)
        return f"*{match.group(1)}*"

    def _apply_with_escape_guard(pattern: re.Pattern[str], repl) -> str:
        chunks: list[str] = []
        last = 0
        for match in pattern.finditer(temp):
            start = match.start()
            if start > 0 and temp[start - 1] == "\\":
                continue
            chunks.append(temp[last:start])
            chunks.append(repl(match))
            last = match.end()
        chunks.append(temp[last:])
        return "".join(chunks)

    temp = _apply_with_escape_guard(STRONG_UNDERSCORE_RE, strong_repl)
    temp = _apply_with_escape_guard(EMPHASIS_UNDERSCORE_RE, emphasis_repl)
    temp = temp.replace("\\\\*\\_", "\\\\_\\_")
    temp = temp.replace("\\\\_\\*", "\\\\_\\_")
    temp = temp.replace("\\\\*\\*", "\\\\_\\_")
    for token, original in placeholders.items():
        temp = temp.replace(token, original)
    return temp


def _is_table_block_start(lines: list[str], index: int) -> bool:
    """Check whether the current position begins a table block."""
    if index + 1 >= len(lines):
        return False
    return _looks_like_table_row(lines[index]) and _is_table_separator_line(lines[index + 1])


def _normalize_table_block(lines: list[str], start: int) -> tuple[list[str], int, Counter[str]]:
    """Normalize markdown table rows and separator lines."""
    block_lines: list[str] = []
    i = start
    while i < len(lines):
        current = lines[i]
        if not current.strip():
            break
        stripped = current.strip()
        if not (_looks_like_table_row(stripped) or _is_table_separator_line(stripped)):
            break
        block_lines.append(stripped)
        i += 1

    normalized: list[str] = []
    stats: Counter[str] = Counter()
    for line in block_lines:
        if _is_table_separator_line(line):
            new_line = _normalize_table_separator_line(line)
            normalized.append(new_line)
            if new_line != line:
                stats["table_separator"] += 1
        else:
            new_line = _normalize_table_row_line(line)
            normalized.append(new_line)
            if new_line != line:
                stats["table_cells"] += 1

    return normalized, len(block_lines), stats


def _looks_like_table_row(line: str) -> bool:
    """Determine if a stripped line resembles a table row."""
    stripped = line.strip()
    if not stripped or stripped.startswith("`"):
        return False
    pipe_count = stripped.count("|")
    return pipe_count >= 1


def _is_table_separator_line(line: str) -> bool:
    """Return True when the line is a table separator."""
    return bool(TABLE_SEPARATOR_RE.match(line.strip()))


def _normalize_table_row_line(line: str) -> str:
    """Normalize spacing and pipes within a table row."""
    cells = _split_table_cells(line)
    normalized_cells = [_normalize_inline_markup(cell.strip()) for cell in cells]
    return "| " + " | ".join(normalized_cells) + " |"


def _normalize_table_separator_line(line: str) -> str:
    """Normalize alignment markers within a separator line."""
    cells = _split_table_cells(line)
    normalized_cells = [_normalize_table_separator_cell(cell) for cell in cells]
    return "| " + " | ".join(normalized_cells) + " |"


def _split_table_cells(line: str) -> list[str]:
    """Split a table row into its constituent cell strings."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    parts = stripped.split("|")
    return parts if parts else [""]


def _normalize_table_separator_cell(cell: str) -> str:
    """Canonicalize a single table separator cell."""
    stripped = cell.strip()
    align_left = stripped.startswith(":")
    align_right = stripped.endswith(":") and len(stripped) > 0
    dash_count = stripped.count("-")
    if dash_count < 3:
        dash_count = 3
    dashes = "-" * dash_count
    if align_left and align_right:
        return f":{dashes}:"
    if align_left:
        return f":{dashes}"
    if align_right:
        return f"{dashes}:"
    return dashes


def _normalize_atx_heading(line: str) -> str:
    """Normalize ATX heading spacing and trailing decorations."""
    stripped = line.strip()
    match = ATX_HEADING_RE.match(stripped)
    if not match:
        return stripped
    marker = match.group("marker")
    body = match.group("body") or ""
    body = body.strip()
    # Remove trailing hash decorations (e.g., '### Title ###').
    body = re.sub(r"\s*#+\s*$", "", body)
    if body:
        body = _collapse_spaces(body)
    return f"{marker} {body}".rstrip()
