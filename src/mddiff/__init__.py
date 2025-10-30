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
]
