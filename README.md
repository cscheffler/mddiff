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
from mddiff import InlineDiffConfig, diff, render_unified

result = diff("old text\n", "new text\n")
if result.has_changes:
    print(render_unified(result))

# Tune inline diff sensitivity by passing InlineDiffConfig.
config = InlineDiffConfig(min_ratio=0.5)
result = diff("alpha\n", "beta\n", inline_config=config)
```

See `tests/` for additional examples of working with the diff data structures.
