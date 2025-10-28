# 4Ls Retrospective (2025-02-14)

## Loved
- Having tight regression fixtures that directly mirror the bugs from the lesson plans.
- Seeing the normalization pipeline handle real-world Markdown quirks after the targeted fixes.

## Learned
- Escape-aware regex replacement is essential when sanitizing Markdown without destroying literal sequences.
- Long `#` separators can masquerade as headings, so block detection needs context, not just patterns.

## Lacked
- Faster feedback when individual pytest targets time out in the CLI harness.
- Automated linting to catch future regressions around escaped characters.

## Longed For
- A dedicated suite of fixtures covering broader Markdown variants (tables with emphasis, backslash-heavy math) to regress against proactively.
- Time to refactor `_normalize_inline_markup` into smaller units with clearer responsibilities.
