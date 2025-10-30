from mddiff import ChangeType, InlineDiffConfig, diff, render_unified


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


def test_inline_config_can_disable_inline_diffing():
    config = InlineDiffConfig(min_ratio=0.9)
    result = diff("value one\n", "value two\n", inline_config=config)

    kinds = [line.kind for line in result.lines]
    assert kinds == [ChangeType.DELETED, ChangeType.INSERTED]


def test_diff_context_zero_emits_only_change_lines():
    left = "- alpha\n- beta\n- charlie\n"
    right = "- alpha\n- beta two\n- charlie\n"

    result = diff(left, right, context=0)

    kinds = [line.kind for line in result.lines]
    assert kinds == [ChangeType.SKIPPED, ChangeType.EDITED]
    header = result.lines[0]
    assert header.left_text.startswith("@@ -2,1 +2,1 @@")
    assert result.lines[1].kind is ChangeType.EDITED
    assert result.context == 0


def test_diff_context_includes_surrounding_lines():
    left = "- alpha\n- beta\n- charlie\n"
    right = "- alpha\n- beta two\n- charlie\n"

    result = diff(left, right, context=1)

    kinds = [line.kind for line in result.lines]
    assert kinds == [
        ChangeType.SKIPPED,
        ChangeType.UNCHANGED,
        ChangeType.EDITED,
        ChangeType.UNCHANGED,
    ]
    assert result.context == 1
    rendered = render_unified(result)
    assert rendered.startswith("@@ -1,3 +1,3 @@\n")
    assert " - alpha\n" in rendered
    assert "- - beta\n" not in rendered
    assert "-- beta\n" in rendered
    assert "+- beta{+ two+}\n" in rendered


def test_diff_negative_context_raises():
    left = "alpha\n"
    right = "beta\n"

    try:
        diff(left, right, context=-1)
    except ValueError as exc:
        assert "context" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for negative context")
