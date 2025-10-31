from __future__ import annotations

from pathlib import Path

from mddiff import HtmlRenderOptions, default_html_styles, diff, render_html


def test_render_html_without_styles(tmp_path: Path) -> None:
    left = "A\n"
    right = "B\n"
    result = diff(left, right)
    options = HtmlRenderOptions(include_styles=False, show_line_numbers=False, layout="split")

    html = render_html(result, options)
    assert "<style" not in html
    assert "mddiff-gutter--hidden" in html


def test_render_html_stylesheet_standalone() -> None:
    css = default_html_styles("custom")
    assert ".custom-diff" in css
    assert "custom-diff--layout-unified" in css


def test_render_html_handles_skipped_hunks():
    base = "- alpha\n- beta\n- gamma\n"
    updated = "- alpha\n- beta two\n- gamma\n"
    result = diff(base, updated, context=0)

    html_split = render_html(result, HtmlRenderOptions(layout="split"))
    html_unified = render_html(result, HtmlRenderOptions(layout="unified"))

    assert "data-change-kind=\"skipped\"" in html_split
    assert "data-left-start" in html_split
    assert "data-change-kind=\"skipped\"" in html_unified
