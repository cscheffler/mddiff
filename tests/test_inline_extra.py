from __future__ import annotations

from mddiff.inline import diff_inline
from mddiff.models import ChangeType


def test_diff_inline_handles_trailing_newline_changes():
    segments = diff_inline("Line one\n", "Line one")
    kinds = [segment.kind for segment in segments]
    assert kinds[-1] is ChangeType.DELETED


def test_diff_inline_whitespace_bridge_merge():
    left = "Value A    B\n"
    right = "Value A B\n"
    segments = diff_inline(left, right)
    assert any(seg.kind is ChangeType.EDITED for seg in segments)
