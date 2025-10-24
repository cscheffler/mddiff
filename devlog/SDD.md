# Markdown Diff Library Software Design Document

## 1. Introduction
The Markdown Diff Library ("mddiff") provides canonicalized comparison of two Markdown documents and produces a unified diff with line- and word-level granularity. This document describes the design required to build the first production-ready release.

## 2. Objectives and Success Criteria
### 2.1 Goals
- Accept any two Markdown inputs (strings, files, or streams) and normalize them to a deterministic, semantically faithful representation.
- Produce a unified diff that highlights added, removed, and edited lines, and highlights inline word-level modifications inside edited lines.
- Expose both an in-memory data model and a plain-text renderer for the diff results.
- Deliver a core library that can be embedded into other tooling (CLIs, web apps) without additional dependencies beyond Python and selected Markdown packages.

### 2.2 Non-Goals
- Building a feature-rich CLI or GUI application; v1 ships only a minimalist CLI wrapper around the core library.
- Rendering HTML or other non-textual diff outputs (future enhancement).
- Handling non-Markdown inputs or converting between markup languages.

### 2.3 Success Metrics
- Normalization is idempotent: running it twice yields identical output.
- Diff output remains stable under reordering of whitespace-only differences after normalization.
- Unit test coverage ≥ 90% for normalization and diff engines.
- End-to-end diff generation of 100 kB documents completes in under 1 second on a modern laptop.

## 3. Scope and Use Cases
- Library consumer compares two Markdown notes to display line-level changes.
- CI system detects breaking doc changes in PRs and annotates inline modifications.
- Documentation tooling surfaces semantic differences even when authors use different Markdown styles.

## 4. Constraints and Assumptions
- Primary runtime: Python 3.11+.
- External dependencies such as `markdown-it-py` are acceptable in v1; we'll evaluate their footprint for future iterations.
- Ship a simple CLI wrapper (`mddiff` command) that invokes the library diff pipeline.
- Runs without network access and without invoking external binaries (no shelling out to GNU diff/wdiff in the first iteration).
- Markdown flavor: strict CommonMark; normalization preserves source for unsupported extensions rather than emulating GitHub-specific behavior.
- Inputs fit in memory; streaming of arbitrarily large documents is not required or supported in v1.

## 5. System Overview
The library pipeline:
1. Ingest and decode Markdown inputs (`str`, `bytes`, or file-like objects) into Unicode strings.
2. Normalize each document into a canonical sequence of lines (`NormalizedDocument`).
3. Compute structural diff between normalized line sequences, producing `DiffLine` objects flagged as `unchanged`, `inserted`, `deleted`, or `edited`.
4. For `edited` lines, compute inline token-level diffs using `InlineDiffSegment` objects.
5. Provide iterables over diff structures and a formatter that emits unified diff text.

## 6. Detailed Design
### 6.1 Module Layout
- `mddiff.io`: Input adapters for strings, files, and streams.
- `mddiff.normalize`: Normalization pipeline and helpers.
- `mddiff.diff`: Line-level diff engine and orchestration logic.
- `mddiff.inline`: Inline token diff implementation.
- `mddiff.models`: Dataclasses describing normalized documents and diff results.
- `mddiff.render`: Text renderer(s) for diff data structures.
- `mddiff.cli`: Minimal command-line wrapper exposing the core diff pipeline.
- `mddiff.utils`: Shared helpers (tokenization, caching, error types).

### 6.2 Normalization Subsystem (`mddiff.normalize`)
**External dependency**: use `markdown-it-py` for CommonMark-compliant parsing, optionally with `mdformat`-style normalization routines where applicable. For v1 we will ship with these dependencies and evaluate their footprint post-release; if they prove too heavy, fall back to a custom rule-based normalizer (see notes below).

**Pipeline**
1. **Pre-processing**: normalize line endings to `\n`; strip leading BOM; ensure UTF-8 decoding.
2. **Parsing**: feed the string into `markdown-it-py` to obtain an AST/token stream.
3. **Canonicalization Rules**:
   - Paragraphs: join soft-wrapped lines into a single line with single spaces.
   - Lists: normalize indentation (4 spaces for nested blocks), convert bullets to `-`, convert ordered list numbers to `1.` while preserving nesting depth.
   - Code blocks: maintain fenced code content verbatim, but normalize fence markers to ``` ``` with language annotations preserved.
   - Headings: standardize to ATX form (`#`, `##`, ...). Strip trailing hashes; ensure single space between `#` and title.
   - Block quotes: ensure `> ` prefix with single space; normalize nested quotes to multiple `>` characters without additional spaces.
   - Horizontal rules: convert to `---`.
   - Table rows: compress consecutive spaces; align pipes without requiring table reformatting (just ensure leading/trailing pipe consistency).
   - Inline emphasis/strong: canonicalize to `*` and `**` respectively.
4. **Serialization**: walk the normalized AST and emit deterministic Markdown text.
5. **Post-processing**: trim extraneous blank lines at file start/end, ensure single trailing newline, and split into logical lines with newline terminators preserved for later diffing.

**Artifact**: `NormalizedDocument` dataclass storing `lines: list[str]`, `metadata` (original length, normalization stats), and `hash` for caching.

### 6.3 Line Diff Engine (`mddiff.diff`)
- Apply a hybrid strategy combining `difflib.SequenceMatcher` (for longest common subsequence) with heuristics to align structurally similar blocks (headings, list items).
- Precompute hashes for normalized lines to speed comparisons.
- For near-duplicate lines, compute similarity ratio; treat as candidates for `edited` rather than `deleted+inserted` when ratio > configurable threshold (default 0.6).
- Generate `DiffLine` objects with attributes: `type`, `original_line`, `modified_line`, `line_no_original`, `line_no_modified`, `segments` (populated lazily for edited lines).
- Provide streaming interface: generator that yields diff lines on demand to handle larger documents without retaining the entire diff in memory at once.

### 6.4 Inline Diff Engine (`mddiff.inline`)
- Tokenize lines into words, punctuation, and intra-word delimiters via regex (`r"\w+|\s+|[^\w\s]"`). Preserve whitespace tokens to allow precise re-rendering.
- Use dynamic programming (Levenshtein distance) or `difflib.SequenceMatcher` on tokens to compute inline changes.
- Collapse consecutive insertions/deletions into grouped segments to avoid noisy output.
- Result: list of `InlineDiffSegment(type, text)` where `type in {unchanged, inserted, deleted, replaced}`; `replaced` holds both original and new text.
- Provide utility to lazily compute segments when first accessed to avoid unnecessary inline diff costs for lines that may be filtered out by consumers.

### 6.5 Data Model (`mddiff.models`)
```python
@dataclass(frozen=True)
class NormalizedDocument:
    source_id: str
    lines: tuple[str, ...]
    metadata: NormalizationMetadata

@dataclass(frozen=True)
class DiffLine:
    type: DiffType  # Enum: UNCHANGED, INSERTED, DELETED, EDITED
    original_line_no: int | None
    modified_line_no: int | None
    original_text: str | None
    modified_text: str | None
    segments: tuple[InlineDiffSegment, ...] | None

@dataclass(frozen=True)
class InlineDiffSegment:
    type: InlineDiffType  # Enum: UNCHANGED, INSERTED, DELETED, REPLACED
    original: str | None
    modified: str | None
```
- Include metadata structures to expose normalization diagnostics (e.g., number of bullet style changes) for testing/insight.

### 6.6 Rendering (`mddiff.render`)
- Default renderer: unified diff style output with prefixes ` ` (unchanged), `+`, `-`, and `~` (edited) at line level.
- Inline edits: wrap insertions with `{+ +}`, deletions with `[- -]`, and replacements showing both forms (e.g., `[-old-]{+new+}`). Provide optional colorization hooks but keep core renderer plain-text.
- Expose `render_unified(diff_iterable, *, show_inline=True) -> str` and streaming variant `iter_render_unified(...) -> Iterator[str]`.

### 6.7 Public API Surface
- `normalize(text: str, *, source_id="left") -> NormalizedDocument`
- `diff(left: str | NormalizedDocument, right: str | NormalizedDocument) -> Iterable[DiffLine]` (v1 relies on baked-in defaults rather than exposed configuration toggles)
- `render(diff_lines: Iterable[DiffLine], *, show_inline=True) -> str`
- CLI entry point `main(argv: Sequence[str] | None = None) -> int` in `mddiff.cli` providing a thin wrapper around library calls.

### 6.8 Configuration & Extensibility
- V1 hard-codes sensible defaults; configuration hooks (e.g., `DiffConfig`) remain internal and undocumented until we validate the default experience.
- Plug-in hooks for custom normalization rules: register new rule functions that receive AST nodes (future enhancement).

### 6.9 Error Handling & Logging
- Raise `NormalizationError`, `DiffComputationError`, `RenderError` for recoverable issues.
- Validate input types early and raise `TypeError` or `ValueError` with actionable messages.
- Provide optional logger integration using Python's standard logging with structured messages for performance profiling.

### 6.10 Performance Considerations
- Memoize normalization results keyed by document hash; expose cache interface for callers.
- Use iterative generators to reduce memory; only materialize inline segments when requested.
- Benchmark against 1 MB docs; identify hot spots (likely tokenization) and optimize using compiled regex or `rapidfuzz` if acceptable.

### 6.11 Testing Strategy
- Unit tests per module covering normalization rules, diff algorithms, and renderer formatting.
- Property-based tests ensuring normalization idempotency and diff symmetry (`diff(A, A)` yields only unchanged lines).
- Snapshot tests for representative Markdown fixtures (lists, tables, headings, code blocks, emphasis).
- Performance regression tests measuring diff latency on synthetic large docs.
- Fuzzing with random Markdown snippets to catch parser edge cases.
- TODO: curate and version a corpus of real Markdown documents for regression coverage.

### 6.12 Tooling & Packaging
- Package as `mddiff` with `pyproject.toml` using Poetry or setuptools; ensure optional extras for formatters.
- Declare console entry point `mddiff = mddiff.cli:main` so the minimal CLI ships with the package.
- Type checking via `mypy`; linting via `ruff`.
- Continuous integration running lint, type check, tests, and benchmarks (benchmarks optional in CI due to time).

### 6.13 Milestones
1. **Normalization MVP**: implement core rules, ensure idempotency, unit tests.
2. **Line Diff Engine**: integrate normalization output with SequenceMatcher, basic diff data model.
3. **Inline Diffing**: token diff, integrate with edited lines, validate default heuristics.
4. **Rendering & API polish**: finalize public API, add text renderer, documentation.
5. **Hardening**: performance profiling, additional tests, packaging, release candidate.

## 7. Security & Privacy
- Library operates on in-memory strings provided by caller; does not persist data.
- No external network calls; ensure dependencies do not execute arbitrary code during parsing.
- Respect caller-provided data by avoiding logging document contents unless debug mode explicitly enabled.

## 8. Risks and Mitigations
- **Normalization parity gaps**: Markdown variants may diverge from CommonMark. Mitigation: capture fixtures from reported cases, adjust rule defaults, and consider targeted opt-outs if defaults prove insufficient.
- **Performance regressions on large tables or code blocks**: Guard expensive paths (skip inline tokenization for oversized lines) and profile for future streaming needs.
- **Dependency stability**: `markdown-it-py` updates could alter AST behavior. Lock dependency version range and add contract tests.
- **Inline diff noise**: Overly granular diffs reduce readability. Tune minimum token length and grouping heuristics; surface configurability only after defaults prove insufficient.

## 9. Documentation Plan
- API reference generated via Sphinx or MkDocs.
- Tutorials demonstrating basic normalization and diff usage.
- Contribution guide with coding standards and testing instructions.

## 10. Outstanding Questions
- None; current decisions unblock development. Reopen this section if new risks or unknowns surface.
