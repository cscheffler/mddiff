from collections import Counter
from pathlib import Path

from mddiff import ChangeType, InlineDiffConfig, diff, render_unified

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "diff"


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_diff_complex_markdown_constructs():
    left = _load("complex_left.md")
    right = _load("complex_right.md")

    config = InlineDiffConfig(min_real_quick_ratio=0.1, min_quick_ratio=0.2, min_ratio=0.25)
    result = diff(left, right, inline_config=config)

    heading_line = next(line for line in result.lines if line.left_text == "# Overview\n")
    assert heading_line.kind is ChangeType.EDITED
    assert heading_line.segments[1].right_text == " Update"

    bullet_zero = next(line for line in result.lines if line.right_text == "- Item zero\n")
    assert bullet_zero.kind is ChangeType.INSERTED

    beta_row = next(line for line in result.lines if line.left_text == "| Beta | 2 |\n")
    assert beta_row.kind is ChangeType.EDITED
    assert beta_row.segments[1].left_text == "2"
    assert beta_row.segments[1].right_text == "3"

    new_row = next(line for line in result.lines if line.right_text == "| Gamma | 5 |\n")
    assert new_row.kind is ChangeType.INSERTED

    code_line = next(line for line in result.lines if line.left_text == "    return a + b\n")
    assert code_line.kind is ChangeType.EDITED
    assert code_line.segments[1].left_text == "return"
    assert code_line.segments[1].right_text == "total ="

    inserted_return = next(line for line in result.lines if line.right_text == "    return total\n")
    assert inserted_return.kind is ChangeType.INSERTED

    nested_quote = next(line for line in result.lines if line.right_text == ">> Nested thought\n")
    assert nested_quote.kind is ChangeType.INSERTED

    footer_line = next(
        line
        for line in result.lines
        if line.left_text == 'def footer_note(): return "done"\n'
    )
    assert footer_line.kind is ChangeType.DELETED
    assert footer_line.segments == ()

    appendix_header = next(line for line in result.lines if line.right_text == "# Appendix\n")
    assert appendix_header.kind is ChangeType.INSERTED

    rendered = render_unified(result)
    expected = (
        "-# Overview\n"
        "+# Overview{+ Update+}\n"
        " \n"
        "+- Item zero\n"
        " - Item one\n"
        " - Item two\n"
        " \n"
        " | Column | Value |\n"
        " | --- | --- |\n"
        " | Alpha | 1 |\n"
        "-| Beta | [-2-] |\n"
        "+| Beta | {+3+} |\n"
        "+| Gamma | 5 |\n"
        " \n"
        " ``` python\n"
        " def add(a, b):\n"
        "-    [-return-] a + b\n"
        "+    {+total =+} a + b\n"
        "+    return total\n"
        " ```\n"
        " \n"
        " > Quote line\n"
        "+>> Nested thought\n"
        " \n"
        "-def footer_note(): return \"done\"\n"
        "+# Appendix\n"
        "+\n"
        "+The footer now lives here.\n"
    )
    assert rendered == expected


def test_diff_large_documents_handles_bulk_changes():
    left = _load("large_left.md")
    right = _load("large_right.md")

    result = diff(left, right)
    counts = Counter(line.kind for line in result.lines)

    assert counts[ChangeType.UNCHANGED] > 100
    assert counts[ChangeType.EDITED] == 15
    assert counts[ChangeType.INSERTED] == 9

    metric_update = next(line for line in result.lines if line.left_text == "- Metric 3.B\n")
    assert metric_update.kind is ChangeType.EDITED
    assert metric_update.segments[1].right_text == " (updated)"

    extra_metric = next(line for line in result.lines if line.right_text == "- Metric 4.C new\n")
    assert extra_metric.kind is ChangeType.INSERTED

    snapshot_change = next(
        line
        for line in result.lines
        if line.left_text == "Results snapshot 5 remains stable.\n"
    )
    assert snapshot_change.kind is ChangeType.EDITED
    assert [segment.kind for segment in snapshot_change.segments] == [
        ChangeType.UNCHANGED,
        ChangeType.EDITED,
        ChangeType.UNCHANGED,
    ]
    assert snapshot_change.segments[1].left_text == "remains stable"
    assert snapshot_change.segments[1].right_text == "now reflects refactor"

    throughput_change = next(line for line in result.lines if line.left_text == "| throughput | 20 |\n")
    assert throughput_change.kind is ChangeType.EDITED
    assert throughput_change.segments[1].right_text == "24"

    latency_insert = next(line for line in result.lines if line.right_text == "| latency | 30 |\n")
    assert latency_insert.kind is ChangeType.INSERTED

    appendix_header = next(line for line in result.lines if line.right_text == "## Appendix\n")
    assert appendix_header.kind is ChangeType.INSERTED
