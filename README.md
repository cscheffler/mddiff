# mddiff

Normalization and diff tooling for Markdown documents.

## Installation

Clone the repository and install the package in editable mode:

```bash
pip install -e .
```

This provides the `mddiff` console command and exposes the Python library APIs.

If you only need the CLI, you can also install straight from the source tree:

```bash
pip install .
```

## CLI Usage

The CLI compares two Markdown documents, running normalization before diffing so stylistic differences are minimized.

```bash
mddiff path/to/left.md path/to/right.md
```

- Exit status `0` indicates no differences were found, while `1` indicates changes.
- Use `-` to read one side from standard input, e.g. `mddiff - path/to/right.md`. (Both sides cannot be `-`.)
- Passing `--version` prints the CLI version and exits.
- Inline diff sensitivity can be tuned via `--inline-min-real-quick`, `--inline-min-quick`, and `--inline-min-ratio`.
- Use `--context N` to limit output to `N` unchanged lines around each change (omit the flag for full context).

Sample output:

```
-Value [-one-]
+Value {+two+}
```

Example forcing full-line replacements:

```bash
mddiff --inline-min-ratio 0.9 left.md right.md
```

## Library Usage

```python
from pathlib import Path

from mddiff import InlineDiffConfig, HtmlRenderOptions, diff, render_html, render_unified

result = diff("old text\n", "new text\n")
if result.has_changes:
    print(render_unified(result))

# Tune inline diff sensitivity by passing InlineDiffConfig.
config = InlineDiffConfig(min_ratio=0.5)
result = diff("alpha\n", "beta\n", inline_config=config)

# Render HTML with default inline stylesheet
if result.has_changes:
    html = render_html(result)
    Path("diff.html").write_text(html, encoding="utf-8")

# Override the class prefix, skip embedding styles, and switch to unified layout
options = HtmlRenderOptions(include_styles=False, class_prefix="docs", layout="unified")
render_html(result, options=options)
```

See `tests/` for additional examples of working with the diff data structures.

## Library Reference

### `normalize`

- Accepts `str`, `bytes`, or file-like objects and coerces them to UTF-8 text before processing (`source_id` defaults to `"unknown"`).
- Normalizes line endings to `\n`, strips UTF-8 BOMs, trims leading/trailing blank blocks, and guarantees a trailing newline so downstream diffs have stable anchors.
- Canonicalizes Markdown structure while counting changes in `NormalizationMetadata.transformations`:
  - Fenced code: markers become triple backticks (` ``` `) with preserved language hints and auto-closing of unterminated fences.
  - Headings: setext underlines become ATX (`#`, `##`), ATX headings lose trailing hashes, and internal whitespace collapses to single spaces.
  - Lists: unordered bullets normalize to `-`, ordered lists renumber to `1.` with multiples-of-four indentation; nested content respects escape-aware inline cleanup.
  - Block quotes: redundant spaces after `>` collapse, nested quotes keep consistent `>` depth, and empty quote lines become bare markers.
  - Horizontal rules normalize to `---`.
  - Tables: cell spacing and alignment markers are rebuilt (`|` padded, separator dashes elongated to ≥3, alignment colons retained), with inline emphasis normalized inside cells.
  - Paragraphs: soft-wrapped text collapses to single-space-separated lines and inline underscores convert to `*`/`**` unless escaped or inside code.
- Returns a `NormalizedDocument` containing `lines` (tuple of strings with newline terminators), `metadata` (lengths + counters), `digest` (SHA-256 of the normalized text), and `source_id`.
- Convenience helpers:
  - `NormalizedDocument.text` reassembles the document (`"".join(lines)`), preserving the canonical trailing newline.
  - `NormalizationMetadata.original_length` / `normalized_length` allow you to audit the shrink/grow ratio before storing results.

Example introspecting transformation counters:

```python
doc = normalize(raw_text, source_id="report.md")
print(doc.metadata.transformations.get("unordered_list_marker", 0))
print(doc.metadata.transformations.get("table_separator", 0))
```

### `diff`

- Accepts raw Markdown strings (or bytes/file-like objects) or precomputed `NormalizedDocument` instances. When strings are passed, `normalize` is invoked internally; use `left_id` / `right_id` to label the sources in metadata.
- Returns a `DiffResult` capturing the normalized left/right documents and a tuple of `DiffLine` entries.
- Optional parameters:
  - `inline_config`: `InlineDiffConfig` instance controlling when replacements stay inline (defaults detailed below).
  - `context`: `None` (full diff) or a non-negative integer limiting unchanged lines around edits. Setting `0` emits only change hunks with unified headers. Negative values raise `ValueError`.
- Pairing logic:
  - Computes opcodes with `difflib.SequenceMatcher(autojunk=False)` on normalized line tuples.
  - `replace` operations become inline edits when similarity thresholds pass; otherwise they degrade into delete/insert pairs to reduce noise.
- Use `diff_normalized(left_doc, right_doc, ...)` when you already have normalized outputs and want to skip re-normalization (e.g., caching or comparing multiple branches).

### `InlineDiffConfig`

- Thresholds gate the `SequenceMatcher` heuristics used in `_should_inline`:
  - `min_real_quick_ratio` (default `0.2`)
  - `min_quick_ratio` (default `0.3`)
  - `min_ratio` (default `0.35`)
- Inline diffs emit `{+insertions+}` and `[-deletions-]` for the differing spans. Raising any threshold pushes borderline replacements into line-level delete/insert pairs.
- Pass `InlineDiffConfig(min_ratio=0.9)` to mimic a diff that only treats near-identical lines as edited, or supply a fully custom config via CLI flags (`--inline-min-*`).

### `DiffResult` and `DiffLine`

- `DiffResult.lines` is a tuple of `DiffLine` objects ordered as they appear in the unified diff.
- `DiffResult.has_changes` is the quick check for “should we display anything?” and stays `False` only when every `DiffLine.kind` is `ChangeType.UNCHANGED`.
- `DiffLine` fields:
  - `kind`: `ChangeType.UNCHANGED`, `INSERTED`, `DELETED`, `EDITED`, or `SKIPPED` (the latter marks synthetic hunk headers when `context` is applied).
  - `left_lineno` / `right_lineno`: 1-based positions in the normalized documents, `None` when the side is absent.
  - `left_text` / `right_text`: full line content including newline terminators.
  - `segments`: tuple of `InlineDiffSegment` objects (for edited lines) detailing inline change spans; empty tuple for unchanged or structural deletions/insertions.
- `InlineDiffSegment` uses the same `ChangeType` enum and stores `left_text` / `right_text` payloads so custom renderers can rebuild context-sensitive displays.

### Rendering

- `render_unified(diff_result)` produces a diff-like string with unified headers (`@@ -l,c +r,c @@`), `-` / `+` prefixes, and inline `{+ +}` / `[- -]` markers.
- `render_html(diff_result, options=None)` returns a styled HTML snippet (optionally including a `<style>` block) with semantic class names for lines, gutters, markers, and inline segments. Use `HtmlRenderOptions` to toggle stylesheet embedding, rename the class prefix, show/hide line numbers, or choose between `split` (side-by-side) and `unified` layouts. Call `default_html_styles()` when you want a standalone stylesheet string.
- The renderer preserves trailing newlines from the source lines via dedicated inline segments, ensuring round-tripping when piping back into files or patch tooling.
- If you supply your own renderer, treat `ChangeType.SKIPPED` as metadata (not a content change) and skip those lines when aggregating change statistics.

### Error Handling & Guarantees

- `normalize` raises `TypeError` for unsupported input types (anything without a readable interface) and assumes UTF-8 for byte streams.
- `diff` / `diff_normalized` raise `ValueError` when `context` is negative; other parameters fall back to well-defined defaults.
- Normalization is idempotent: `normalize(normalize(text).text)` yields the same digest and line tuple (enforced by `tests/test_real_documents.py`).
- Large-document performance is defended with fixtures covering 100 kB inputs within a one-second budget (`tests/test_performance.py`).

## Integration Patterns

- **Cache normalization results**: Use `NormalizedDocument.digest` as a content hash to skip re-normalization or to persist normalized snapshots alongside originals.
- **Reuse normalized inputs**: When diffing a document against many revisions, call `normalize` once per version and feed the cached `NormalizedDocument` instances into `diff_normalized`.
- **Tune inline noise**: Start with the defaults, then lower thresholds for prose-heavy docs (more inline highlights) or raise them for code-focused diffs where line-level clarity matters.
- **Context-aware presentation**: Pass `context=0` for change-only summaries (e.g., CI annotations) or a higher number for user-facing review tools. Remember CLI’s `--context` flag maps directly to the same behavior.
- **Transformation metrics**: Leverage `NormalizationMetadata.transformations` to alert when normalization makes unexpected changes (e.g., list bullet rewrites) in automated pipelines.
- **Streaming & memory**: `diff` yields `DiffLine` entries in order; if you need streaming consumption, iterate `DiffResult.lines` without forcing `render_unified` and emit as you go.

## CLI Parity

- CLI flags mirror the library surface:
  - `--inline-min-real-quick`, `--inline-min-quick`, `--inline-min-ratio` map to `InlineDiffConfig` fields.
  - `--context` matches the `context` parameter on `diff`.
- Use `--format html-split` for side-by-side HTML or `--format html-unified` for unified HTML instead of text (default: text). The HTML output embeds a minimal stylesheet by default, mirroring `render_html` and its layout-specific classes.
- CLI reads a single side from stdin (`-`) and prevents double-stdin to avoid blocking; exit code `0` means no changes, `1` means differences were detected.
- Rendering matches `render_unified` output, so you can capture CLI output and feed it back into tools expecting standard unified diff formatting.
