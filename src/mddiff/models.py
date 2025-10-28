from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class NormalizationMetadata:
    """Diagnostics captured while normalizing a document."""

    original_length: int
    normalized_length: int
    transformations: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedDocument:
    """Canonical representation of a Markdown document."""

    source_id: str
    lines: tuple[str, ...]
    metadata: NormalizationMetadata
    digest: str

    @property
    def text(self) -> str:
        """Reconstruct the normalized Markdown as a single string."""

        return "".join(self.lines)
