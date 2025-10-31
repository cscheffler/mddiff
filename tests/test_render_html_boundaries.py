from __future__ import annotations

from mddiff import HtmlRenderOptions, diff, render_html


def test_render_html_drop_line_numbers_when_disabled():
    result = diff("a\n", "b\n")
    html = render_html(result, HtmlRenderOptions(show_line_numbers=False))
    assert "data-left-lineno" in html
    assert "mddiff-gutter--hidden" in html
