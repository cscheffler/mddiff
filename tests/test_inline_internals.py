from __future__ import annotations

from mddiff.inline import (
    _combine_segments,
    _coalesce_segments,
    _is_change_segment,
    _is_mergeable_whitespace,
    _merge_whitespace_bridges,
    _segment,
    _strip_trailing_newline,
    _tokenize,
    diff_inline,
)
from mddiff.models import ChangeType, InlineDiffSegment


def test_diff_inline_emits_deletion_segment():
    segments = diff_inline("deleted", "")
    assert segments[0].kind is ChangeType.DELETED


def test_diff_inline_handles_trailing_newline_insert():
    segments = diff_inline("line", "line\n")
    assert segments[-1].kind is ChangeType.INSERTED
    assert segments[-1].right_text == "\n"


def test_tokenize_empty_text():
    assert _tokenize("") == []


def test_strip_trailing_newline_variants():
    body, flag = _strip_trailing_newline("value\n")
    assert body == "value" and flag
    body, flag = _strip_trailing_newline("value")
    assert body == "value" and not flag


def test_coalesce_segments_merges_adjacent_matches():
    segs = (
        InlineDiffSegment(ChangeType.UNCHANGED, left_text="foo", right_text="foo"),
        InlineDiffSegment(ChangeType.UNCHANGED, left_text="bar", right_text="bar"),
    )
    merged = _coalesce_segments(segs)
    assert len(merged) == 1
    assert merged[0].left_text == "foobar"


def test_merge_whitespace_bridges_combines_changes():
    segments = (
        InlineDiffSegment(ChangeType.INSERTED, left_text="", right_text="X"),
        InlineDiffSegment(ChangeType.UNCHANGED, left_text=" ", right_text=" "),
        InlineDiffSegment(ChangeType.DELETED, left_text="Y", right_text=""),
    )
    merged = _merge_whitespace_bridges(segments)
    assert len(merged) == 1
    assert merged[0].kind is ChangeType.EDITED
    assert merged[0].left_text.strip() == "Y"
    assert merged[0].right_text.strip() == "X"


def test_merge_whitespace_bridges_retains_small_sequences():
    segs = (
        InlineDiffSegment(ChangeType.INSERTED, left_text="", right_text="X"),
        InlineDiffSegment(ChangeType.UNCHANGED, left_text=" ", right_text=" "),
    )
    assert _merge_whitespace_bridges(segs) == segs


def test_is_mergeable_whitespace_predicates():
    whitespace = InlineDiffSegment(ChangeType.UNCHANGED, left_text=" ", right_text=" ")
    assert _is_mergeable_whitespace(whitespace)
    newline = InlineDiffSegment(ChangeType.UNCHANGED, left_text="\n", right_text="")
    assert not _is_mergeable_whitespace(newline)
    empty = InlineDiffSegment(ChangeType.UNCHANGED, left_text="", right_text="")
    assert not _is_mergeable_whitespace(empty)


def test_is_change_segment_flags_changes():
    assert _is_change_segment(InlineDiffSegment(ChangeType.DELETED))
    assert not _is_change_segment(InlineDiffSegment(ChangeType.UNCHANGED))


def test_combine_segments_variants():
    left = InlineDiffSegment(ChangeType.DELETED, left_text="A", right_text="")
    whitespace = InlineDiffSegment(ChangeType.UNCHANGED, left_text=" ", right_text=" ")
    right = InlineDiffSegment(ChangeType.INSERTED, left_text="", right_text="B")
    combined = _combine_segments(left, whitespace, right)
    assert combined.kind is ChangeType.EDITED

    left_only = _combine_segments(left, InlineDiffSegment(ChangeType.UNCHANGED, left_text=" ", right_text=""), InlineDiffSegment(ChangeType.INSERTED, left_text="", right_text=""))
    assert left_only.kind is ChangeType.DELETED

    right_only = _combine_segments(
        InlineDiffSegment(ChangeType.DELETED, left_text="", right_text=""),
        InlineDiffSegment(ChangeType.UNCHANGED, left_text="", right_text=""),
        InlineDiffSegment(ChangeType.INSERTED, left_text="", right_text="B"),
    )
    assert right_only.kind is ChangeType.INSERTED


def test_diff_inline_insert_segment():
    segments = diff_inline("", "abc")
    assert segments[0].kind is ChangeType.INSERTED


def test_coalesce_segments_handles_empty():
    assert _coalesce_segments(()) == ()

