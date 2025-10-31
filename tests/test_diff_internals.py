from __future__ import annotations

from typing import Iterable

from mddiff.diff import _apply_context, _build_replaced_lines, _make_hunk_header, _should_inline
from mddiff.models import ChangeType, DiffLine, InlineDiffConfig, NormalizationMetadata, NormalizedDocument


def _doc(lines: Iterable[str], source: str = "doc") -> NormalizedDocument:
    lines = tuple(lines)
    meta = NormalizationMetadata(
        original_length=sum(len(line) for line in lines),
        normalized_length=sum(len(line) for line in lines),
        transformations={},
    )
    return NormalizedDocument(source_id=source, lines=lines, metadata=meta, digest=f"digest-{source}")


def test_build_replaced_lines_emits_leftover_left_lines():
    left = _doc(["A\n", "B\n", "C\n"])
    right = _doc(["A!\n"])

    lines = _build_replaced_lines(left, right, 0, 3, 0, 1, inline_config=None)

    deleted_texts = [line.left_text for line in lines if line.kind is ChangeType.DELETED]
    assert "B\n" in deleted_texts and "C\n" in deleted_texts


def test_build_replaced_lines_emits_leftover_right_lines():
    left = _doc(["A\n"])
    right = _doc(["A!\n", "B!\n", "C!\n"])

    lines = _build_replaced_lines(left, right, 0, 1, 0, 3, inline_config=None)
    inserted_texts = [line.right_text for line in lines if line.kind is ChangeType.INSERTED]
    assert "B!\n" in inserted_texts and "C!\n" in inserted_texts


def test_should_inline_handles_blank_lines():
    assert _should_inline("\n", "\n", None)

    config = InlineDiffConfig(min_real_quick_ratio=1.0, min_quick_ratio=1.0, min_ratio=1.0)
    assert not _should_inline("alpha\n", "beta\n", config)


def test_apply_context_on_empty_and_no_changes():
    assert _apply_context([], context=0) == ()

    unchanged_line = DiffLine(
        kind=ChangeType.UNCHANGED,
        left_lineno=1,
        right_lineno=1,
        left_text="same\n",
        right_text="same\n",
    )
    assert _apply_context([unchanged_line], context=1) == ()


def test_apply_context_emits_headers_for_multiple_blocks():
    lines = [
        DiffLine(ChangeType.UNCHANGED, 1, 1, "a\n", "a\n"),
        DiffLine(ChangeType.INSERTED, None, 2, None, "b\n"),
        DiffLine(ChangeType.UNCHANGED, 2, 3, "c\n", "c\n"),
        DiffLine(ChangeType.DELETED, 3, None, "d\n", None),
    ]

    result = _apply_context(lines, context=0)
    # Expect two change blocks and thus two headers preceding the insert/delete pairs.
    header_count = sum(1 for line in result if line.kind is ChangeType.SKIPPED)
    assert header_count == 2


def test_make_hunk_header_handles_missing_side_numbers():
    lines = [
        DiffLine(ChangeType.INSERTED, None, 5, None, "x\n"),
        DiffLine(ChangeType.DELETED, 7, None, "y\n", None),
    ]

    header = _make_hunk_header(lines, 0, 1, prev_left=0, prev_right=0)
    assert header.left_text.startswith("@@ -7,1 +5,1 @@")
