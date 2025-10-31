from __future__ import annotations

from mddiff.models import (
    ChangeType,
    DiffLine,
    DiffResult,
    InlineDiffConfig,
    InlineDiffSegment,
    NormalizationMetadata,
    NormalizedDocument,
)


def test_normalized_document_text_property():
    meta = NormalizationMetadata(original_length=5, normalized_length=5)
    doc = NormalizedDocument(
        source_id="doc",
        lines=("Line one\n", "Line two\n"),
        metadata=meta,
        digest="digest",
    )

    assert doc.text == "Line one\nLine two\n"


def test_inline_diff_segment_text_variants():
    seg_insert = InlineDiffSegment(ChangeType.INSERTED, left_text="", right_text="abc")
    seg_delete = InlineDiffSegment(ChangeType.DELETED, left_text="abc", right_text="")
    seg_edit = InlineDiffSegment(ChangeType.EDITED, left_text="abc", right_text="xyz")
    seg_same = InlineDiffSegment(ChangeType.UNCHANGED, left_text="abc", right_text="abc")

    assert seg_insert.text == "abc"
    assert seg_delete.text == "abc"
    assert seg_edit.text == "abc"
    assert seg_same.text == "abc"


def test_diff_result_has_changes_property():
    meta = NormalizationMetadata(original_length=3, normalized_length=3)
    doc = NormalizedDocument("doc", ("a\n",), meta, "digest")
    unchanged = DiffLine(
        kind=ChangeType.UNCHANGED,
        left_lineno=1,
        right_lineno=1,
        left_text="a\n",
        right_text="a\n",
    )
    edited = DiffLine(
        kind=ChangeType.EDITED,
        left_lineno=1,
        right_lineno=1,
        left_text="a\n",
        right_text="b\n",
        segments=(InlineDiffSegment(ChangeType.EDITED, "a", "b"),),
    )

    result_clean = DiffResult(left=doc, right=doc, lines=(unchanged,))
    result_dirty = DiffResult(left=doc, right=doc, lines=(unchanged, edited))

    assert not result_clean.has_changes
    assert result_dirty.has_changes


def test_inline_diff_config_defaults():
    config = InlineDiffConfig()
    assert config.min_ratio == 0.35
    assert config.min_quick_ratio == 0.3
    assert config.min_real_quick_ratio == 0.2
