from mddiff import ChangeType, diff, render_unified


def test_diff_identical_documents_yields_unchanged_lines():
    result = diff("Hello world\n", "Hello world\n")

    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.kind is ChangeType.UNCHANGED
    assert line.left_text == "Hello world\n"
    assert line.right_text == "Hello world\n"


def test_diff_reports_insertions():
    left = "- alpha\n- beta\n"
    right = "- alpha\n- beta\n- gamma\n"

    result = diff(left, right)

    kinds = [line.kind for line in result.lines]
    assert kinds == [ChangeType.UNCHANGED, ChangeType.UNCHANGED, ChangeType.INSERTED]
    assert result.lines[-1].right_text == "- gamma\n"


def test_diff_reports_deletions():
    left = "- alpha\n- beta\n- gamma\n"
    right = "- alpha\n- beta\n"

    result = diff(left, right)

    kinds = [line.kind for line in result.lines]
    assert kinds == [ChangeType.UNCHANGED, ChangeType.UNCHANGED, ChangeType.DELETED]
    assert result.lines[-1].left_text == "- gamma\n"


def test_inline_segments_highlight_replacements():
    left = "value one\n"
    right = "value two\n"

    result = diff(left, right)

    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.kind is ChangeType.EDITED
    segments = line.segments
    assert [segment.kind for segment in segments] == [
        ChangeType.UNCHANGED,
        ChangeType.EDITED,
        ChangeType.UNCHANGED,
    ]
    assert segments[1].left_text == "one"
    assert segments[1].right_text == "two"


def test_render_unified_marks_inline_and_line_changes():
    left = "# Title\n\nBeta\n"
    right = "# Title\n\nBeta two\n"

    result = diff(left, right)
    rendered = render_unified(result)

    assert rendered == " # Title\n \n-Beta\n+Beta{+ two+}\n"
