from mddiff import normalize


def test_paragraphs_and_headings_normalized():
    doc = normalize(
        """
Title
=====

Paragraph spread
across lines.

"""
    )

    assert doc.text == "# Title\n\nParagraph spread across lines.\n"


def test_unordered_list_markers_and_indentation():
    doc = normalize(
        """
- item one
  * nested alt
    + deeper

"""
    )

    assert doc.text == """- item one
    - nested alt
    - deeper
"""


def test_ordered_lists_are_renumbered():
    doc = normalize(
        """
10. first
2) second
   3. nested

"""
    )

    assert doc.text == """1. first
1. second
        1. nested
"""


def test_blockquote_prefix_compaction():
    doc = normalize(
        ">   >    Nested quote\n>Plain quote\n"
    )

    assert doc.text == ">> Nested quote\n> Plain quote\n"


def test_horizontal_rules_and_code_fences():
    doc = normalize(
        """
***

~~~python
print("hi")
~~~   

"""
    )

    assert doc.text == "---\n\n``` python\nprint(\"hi\")\n```\n"


def test_bytes_input_and_metadata_counts():
    doc = normalize(b"- a\n* b\n")
    assert doc.text == "- a\n- b\n"
    assert doc.metadata.transformations.get("unordered_list_marker")
    assert len(doc.digest) == 64


def test_tables_are_normalized():
    doc = normalize(
        """
Column A|Column B
:--|--:
value _one_|__two__

"""
    )

    assert (
        doc.text
        == """| Column A | Column B |
| :--- | ---: |
| value *one* | **two** |
"""
    )


def test_inline_emphasis_conversion():
    doc = normalize("This has _italic_ and __bold__ plus snake_case.\n")
    assert doc.text == "This has *italic* and **bold** plus snake_case.\n"


def test_blockquote_nested_content():
    doc = normalize(
        """
> Outer line
>
> > Inner _text_
> > still inner

"""
    )

    assert doc.text == "> Outer line\n>\n>> Inner *text* still inner\n"


def test_whitespace_in_paragraphs_is_collapsed():
    doc = normalize("Paragraph    with\tmixed\nwhitespace.\n\n")
    assert doc.text == "Paragraph with mixed whitespace.\n"


def test_multiple_blank_lines_collapse_to_single():
    doc = normalize("Line one\n\n\n\nLine two\n")
    assert doc.text == "Line one\n\nLine two\n"


def test_trailing_spaces_at_line_end_removed():
    doc = normalize("Line with spaces   \nNext line\t\t\n")
    assert doc.text == "Line with spaces Next line\n"


def test_atx_headings_are_preserved_and_trimmed():
    doc = normalize("###  Heading with  extra   ###\n")
    assert doc.text == "### Heading with extra\n"
