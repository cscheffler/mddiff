# mddiff

Normalization-aware Markdown diffs with both terminal-friendly and HTML renderers.

## Highlights

- Canonicalizes Markdown before diffing so stylistic variations (spacing, list markers, heading styles) do not mask real changes.
- Produces structured diff data (`DiffResult`, `DiffLine`, `InlineDiffSegment`) for programmatic use, plus ready-to-use text and HTML renderers.
- Ships with a zero-dependency CLI that mirrors the Python API and supports unified text, split HTML, and unified HTML output.
- Exposes styling hooks (`HtmlRenderOptions`, `default_html_styles`, `default_html_class_names`) so downstream tooling can own presentation without rewriting the diff logic.

## Quick Start

### Install

```bash
pip install -e .  # editable install for development
```

Use `pip install .` if you only need the CLI.

### CLI

```bash
mddiff path/to/left.md path/to/right.md
```

- Exit code `0` means documents match; `1` indicates differences.
- Read one side from stdin with `-` (only one side may be stdin).
- Key flags:
  - `--inline-min-real-quick`, `--inline-min-quick`, `--inline-min-ratio` tune inline edit sensitivity.
  - `--context N` controls unchanged context around edits (default: full diff).
  - `--format {text, html-split, html-unified}` selects the renderer (default: `text`).

### Python

```python
from pathlib import Path
from mddiff import (
    InlineDiffConfig,
    HtmlRenderOptions,
    diff,
    render_html,
    render_unified,
)

left = "# Title\n\nValue one\n"
right = "# Title\n\nValue two\n"

result = diff(left, right, inline_config=InlineDiffConfig(min_ratio=0.4))

if result.has_changes:
    print(render_unified(result))  # unified text
    html = render_html(result, HtmlRenderOptions(layout="unified"))
    Path("diff.html").write_text(html, encoding="utf-8")
```

## Core Concepts & API

### Normalization (`normalize`)

- Accepts `str`, `bytes`, and file-like objects, always returning UTF-8 text with consistent newlines and a trailing newline.
- Canonicalizes Markdown structure (headings, lists, block quotes, tables, paragraphs, fenced code) and tracks each transformation in `NormalizationMetadata.transformations`.
- Returns a `NormalizedDocument` with normalized `lines`, `metadata`, a stable `digest`, and convenience helpers like `.text`.

### Diffing (`diff`, `diff_normalized`)

- Compare raw Markdown strings or pre-normalized documents. Source identifiers (`left_id`, `right_id`) feed metadata.
- Optional `InlineDiffConfig` thresholds decide when replacements stay inline vs. expand to delete/insert pairs.
- Optional `context` keeps surrounding unchanged lines; `None` emits the full diff.
- Outputs a `DiffResult` containing ordered `DiffLine` entries. Each `DiffLine` carries change kind, line numbers, text, and inline `segments` for edited lines.

### Rendering

- `render_unified(diff_result)` emits a unified diff string with `{+ +}` / `[- -]` inline markers.
- `render_html(diff_result, options=None)` renders semantic HTML. `HtmlRenderOptions` toggles stylesheet embedding, renames the class prefix, controls line numbers, and chooses between `split` (side-by-side) and `unified` layouts.
- `default_html_styles(prefix)` returns the inline CSS used by `render_html` for a given prefix so you can host the stylesheet separately.

## HTML Styling Reference

`render_html` keeps presentation minimal so callers can compose their own UI. Retrieve the emitted class names with `default_html_class_names(prefix="mddiff")`; the helper returns a dataclass listing every class applied to lines, gutters, segments, and layout containers.

```python
from mddiff import default_html_class_names

classes = default_html_class_names()
print(classes.segment_inserted)  # "mddiff-segment--inserted"
```

When re-rendering the Markdown content yourself, preserve (or map) these classes to keep diff colouring and strikethroughs intact.

## CLI Reference

- `mddiff LEFT RIGHT` — primary entry point. LEFT/RIGHT are file paths or `-` for stdin (only one side may use stdin).
- `--inline-min-real-quick`, `--inline-min-quick`, `--inline-min-ratio` — pass-through to `InlineDiffConfig` thresholds.
- `--context N` — show `N` unchanged lines of context around each change; `0` shows only change hunks.
- `--format {text, html-split, html-unified}` — select renderer (text is default).
- `--version` — print package version.

Output is written to stdout; errors (e.g., invalid arguments) surface on stderr.

## Integration Tips

- **Cache normalized snapshots:** reuse `NormalizedDocument` instances and their `digest` to avoid repeated normalization.
- **Tune inline noise:** lower ratio thresholds for prose to emphasize inline edits; raise them for code so full-line replacements are clearer.
- **Stream results:** iterate `DiffResult.lines` directly if you want to process diffs without materializing renderer output.
- **Highlight metrics:** use `NormalizationMetadata.transformations` to detect when normalization rewrote specific structures (e.g., list markers).

## Guarantees & Error Handling

- `normalize` raises `TypeError` for unsupported input types; `diff`/`diff_normalized` raise `ValueError` for negative `context`.
- Normalization is idempotent (`normalize(normalize(text).text)` yields the same document).
- Large-document performance is covered by regression tests (100 kB fixtures complete in under one second).

See the `tests/` directory for executable examples and regression coverage.
