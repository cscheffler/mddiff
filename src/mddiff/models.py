from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple


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


class ChangeType(str, Enum):
    """Kinds of changes tracked at both line and inline granularity."""

    UNCHANGED = "unchanged"
    INSERTED = "inserted"
    DELETED = "deleted"
    EDITED = "edited"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class InlineDiffSegment:
    """Inline diff segment within an edited line."""

    kind: ChangeType
    left_text: str = ""
    right_text: str = ""

    @property
    def text(self) -> str:
        """Convenience accessor for the visible text of this segment."""

        if self.kind is ChangeType.INSERTED:
            return self.right_text
        if self.kind is ChangeType.DELETED:
            return self.left_text
        if self.kind is ChangeType.EDITED:
            return self.left_text
        return self.left_text


@dataclass(frozen=True)
class DiffLine:
    """Represents a single line in the unified diff view."""

    kind: ChangeType
    left_lineno: int | None
    right_lineno: int | None
    left_text: str | None
    right_text: str | None
    segments: Tuple[InlineDiffSegment, ...] = ()

    @property
    def is_edited(self) -> bool:
        return self.kind is ChangeType.EDITED


@dataclass(frozen=True)
class DiffResult:
    """Container for the full diff between two normalized documents."""

    left: NormalizedDocument
    right: NormalizedDocument
    lines: Tuple[DiffLine, ...]
    context: int | None = None

    @property
    def has_changes(self) -> bool:
        """Return True when the diff captured at least one change."""

        return any(line.kind is not ChangeType.UNCHANGED for line in self.lines)


@dataclass(frozen=True)
class InlineDiffConfig:
    """Configuration controlling when inline diffs should be emitted."""

    min_real_quick_ratio: float = 0.2
    min_quick_ratio: float = 0.3
    min_ratio: float = 0.35
