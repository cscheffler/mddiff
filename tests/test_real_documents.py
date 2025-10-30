from pathlib import Path

import pytest

from mddiff import normalize

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "normalize"


@pytest.mark.parametrize(
    "fixture_path",
    sorted(FIXTURE_DIR.glob("*.md")),
    ids=lambda path: path.stem,
)
def test_real_markdown_documents_normalize_cleanly(fixture_path: Path) -> None:
    raw_text = fixture_path.read_text(encoding="utf-8")

    # Initial normalization should succeed and add a trailing newline.
    doc = normalize(raw_text, source_id=fixture_path.name)
    assert doc.text.endswith("\n"), "Normalized text must end with a newline"
    assert doc.metadata.original_length == len(raw_text)
    assert doc.metadata.normalized_length == len(doc.text)

    # Normalization is idempotent when run on the normalized output.
    second_pass = normalize(doc.text, source_id=f"{fixture_path.name}-second")
    assert second_pass.text == doc.text
    assert second_pass.digest == doc.digest

    # Spot-check that the normalization keeps front matter intact if present.
    if raw_text.lstrip().startswith("---\n"):
        assert doc.text.lstrip().startswith("---\n"), "Front matter should survive normalization"
