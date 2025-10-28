"""mddiff package."""

from .models import NormalizationMetadata, NormalizedDocument
from .normalize import normalize

__all__ = ["normalize", "NormalizedDocument", "NormalizationMetadata"]
