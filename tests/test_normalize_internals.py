from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from collections import Counter

import pytest

from mddiff.normalize import (
    _coerce_text,
    _ensure_trailing_newline,
    _indent_depth,
    _is_block_start,
    _is_blockquote_line,
    _is_list_item_line,
    _is_table_block_start,
    _is_table_separator_line,
    _looks_like_table_row,
    _match_fence_start,
    _normalize_atx_heading,
    _normalize_blockquote_block,
    _normalize_blocks,
    _normalize_code_fence,
    _normalize_inline_markup,
    _normalize_line_endings,
    _normalize_list_block,
    _normalize_table_block,
    _normalize_table_row_line,
    _normalize_table_separator_cell,
    _normalize_table_separator_line,
    _normalize_setext_heading,
    _squash_blank_lines,
    _strip_one_blockquote_marker,
    _strip_bom,
    _trim_blank_ends,
    _split_table_cells,
)


def test_coerce_text_variants_and_errors():
    assert _coerce_text("text") == "text"
    assert _coerce_text(b"bytes") == "bytes"
    assert _coerce_text(StringIO("stream")).startswith("stream")
    assert _coerce_text(BytesIO(b"buffer")) == "buffer"

    class Custom:
        def read(self):
            return b"custom"

    class CustomStr:
        def read(self):
            return "string"

    assert _coerce_text(Custom()) == "custom"
    assert _coerce_text(CustomStr()) == "string"

    with pytest.raises(TypeError):
        _coerce_text(object())


def test_trim_blank_ends_and_trailing_newline():
    assert _trim_blank_ends("\n\n") == ""
    assert _ensure_trailing_newline("no-newline") == "no-newline\n"


def test_normalize_line_endings_and_bom():
    text = "line1\r\nline2\rline3"
    assert _normalize_line_endings(text) == "line1\nline2\nline3"
    assert _strip_bom("\ufeffTitle") == "Title"


def test_unterminated_code_fence_adds_closing_marker():
    lines = ["```python", "print('hi')"]
    block, consumed, changed = _normalize_code_fence(lines, 0, _match_fence_start(lines[0]))
    assert block[-1] == "```"
    assert consumed == 3  # original lines plus closing marker
    assert changed >= 1


def test_blockquote_normalization_handles_empty_inner():
    block, consumed, stats = _normalize_blockquote_block([">   "], 0)
    assert block == [">"]
    assert consumed == 1


def test_list_block_breaks_on_non_list():
    block, consumed, stats = _normalize_list_block(["not a list"], 0)
    assert block == []
    assert consumed == 0

    block, consumed, stats = _normalize_list_block(["\t- item"], 0)
    assert block[0].startswith("    -")


def test_is_block_start_variants():
    lines = [
        "```",  # fence
        "> quote",
        "- item",
        "# Heading",
        "***",
        "Setext",
        "====",
        "Paragraph",
    ]
    assert _is_block_start(lines, 0)
    assert _is_block_start(lines, 1)
    assert _is_block_start(lines, 2)
    assert _is_block_start(lines, 3)
    assert _is_block_start(lines, 4)
    assert _is_block_start(lines, 5)
    assert not _is_block_start(lines, 7)


def test_inline_markup_handles_code_and_escapes():
    text = "`code_with__underscores__` and _emphasis_"
    normalized = _normalize_inline_markup(text)
    assert "`code_with__underscores__`" in normalized
    assert "*emphasis*" in normalized


def test_table_detection_and_normalization():
    lines = [
        "| Col | Val |",
        "| --- | :-: |",
        "| A   | 1   |",
        "Not table",
    ]
    assert _is_table_block_start(lines, 0)
    block, consumed, stats = _normalize_table_block(lines, 0)
    assert consumed == 3
    assert "table_separator" in stats
    assert _looks_like_table_row("Col | Val")
    assert _is_table_separator_line("| --- | --- |")

    row = _normalize_table_row_line("|A|B|")
    assert row == "| A | B |"

    sep = _normalize_table_separator_line("|:--|--:|")
    assert sep == "| :--- | ---: |"

    assert _normalize_table_separator_cell(":-:") == ":---:"
    assert _normalize_table_separator_cell(":-") == ":---"
    assert _normalize_table_separator_cell("-:") == "---:"
    assert _normalize_table_separator_cell("-") == "---"


def test_setext_and_atx_heading_normalization():
    assert _normalize_setext_heading("Title", "====") == "# Title"
    assert _normalize_atx_heading("### Title ###") == "### Title"
    assert _normalize_atx_heading("Plain text") == "Plain text"


def test_squash_blank_lines_removes_runs():
    assert _squash_blank_lines(["line", "", "", "other", ""]) == ["line", "", "other"]


def test_split_table_cells_handles_edges():
    assert _split_table_cells("|a|b|") == ["a", "b"]
    assert _split_table_cells("one|two") == ["one", "two"]


def test_is_blockquote_line_detection():
    assert _is_blockquote_line("> nested")
    assert not _is_blockquote_line("plain text")


def test_trim_blank_ends_trailing_newlines():
    assert _trim_blank_ends("Line\n\n") == "Line"






def test_inline_markup_respects_escaped_underscores():
    text = r"\_literal_ and \__strong__"
    normalized = _normalize_inline_markup(text)
    assert normalized.startswith(r"\_literal_")
    assert r"\__strong__" in normalized


def test_strip_one_blockquote_marker_variants():
    assert _strip_one_blockquote_marker("> nested") == "nested"
    assert _strip_one_blockquote_marker("text") == "text"
