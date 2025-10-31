"""mddiff package."""

from .diff import diff, diff_normalized
from .models import (
    ChangeType,
    DiffLine,
    DiffResult,
    InlineDiffConfig,
    NormalizationMetadata,
    NormalizedDocument,
)
from .normalize import normalize
from .render import render_unified
from .render_html import (
    HtmlClassNames,
    HtmlRenderOptions,
    default_html_class_names,
    default_html_styles,
    render_html,
)

__all__ = [
    "normalize",
    "diff",
    "diff_normalized",
    "render_unified",
    "NormalizedDocument",
    "NormalizationMetadata",
    "DiffResult",
    "DiffLine",
    "ChangeType",
    "InlineDiffConfig",
    "render_html",
    "HtmlRenderOptions",
    "default_html_styles",
    "default_html_class_names",
    "HtmlClassNames",
]
