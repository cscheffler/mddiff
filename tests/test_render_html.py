from mddiff import (
    HtmlRenderOptions,
    default_html_class_names,
    diff,
    render_html,
)


def test_render_html_wraps_lines_with_classes():
    result = diff("Value one\n", "Value two\n")

    html = render_html(result)

    assert 'class="mddiff-diff mddiff-diff--layout-split"' in html
    assert 'mddiff-diff--layout-split' in html
    assert 'mddiff-line mddiff-line--edited' in html
    assert 'mddiff-segment--deleted' in html
    assert 'mddiff-segment--inserted' in html


def test_render_html_escapes_html_entities():
    left = "<title>Example & Co.</title>\n"
    right = "<title>Example & Co.</title>\n<script>alert('hi')</script>\n"

    result = diff(left, right)
    html = render_html(result)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&#x27;hi&#x27;" in html


def test_render_html_respects_options():
    result = diff("Alpha\n", "Beta\n")
    options = HtmlRenderOptions(include_styles=False, class_prefix="custom")

    html = render_html(result, options=options)

    assert "<style" not in html
    assert 'class="custom-diff custom-diff--layout-split"' in html


def test_render_html_unified_layout_emits_markers():
    result = diff("Value one\n", "Value two\n")
    options = HtmlRenderOptions(layout="unified")

    html = render_html(result, options=options)

    assert 'mddiff-diff--layout-unified' in html
    assert html.count('mddiff-line mddiff-line--edited') == 1
    assert html.count('mddiff-segment--deleted') >= 1
    assert html.count('mddiff-segment--inserted') >= 1
    assert 'text-decoration-line: line-through;' in html


def test_default_html_class_names_reflect_prefix():
    classes = default_html_class_names("custom")

    assert classes.prefix == "custom"
    assert classes.root == "custom-diff"
    assert classes.root_layout_unified == "custom-diff--layout-unified"
    assert classes.segment_inserted == "custom-segment--inserted"
    assert classes.gutter_left == "custom-gutter--left"
