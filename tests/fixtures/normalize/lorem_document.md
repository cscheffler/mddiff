---
title: Sample Knowledge Share
author: Pat Ipsum
updated: 2024-01-15
---

# mddiff Overview

`mddiff` helps teams understand documentation churn. The library ingests Markdown sources, applies deterministic normalization, and emits structured diff artifacts ready for tooling.

## Highlights

- Fast iteration over Markdown pairs (documents <= 100 kB complete in under a second).
- Rich classification metadata: unchanged, inserted, deleted, and inline replacements.
- Type-safe Python API plus a minimal wrapper CLI.

### Sample Workflow

1. Normalize both the "before" and "after" docs.
2. Feed normalized text into the diff engine.
3. Render a unified view for code review or change logs.

> **Note:** Normalization is idempotent and safe to cache. Teams often reuse cached outputs between CI and local dev.
>
> - CommonMark is the baseline, but unsupported extensions fall back to the literal source text.
> - Code fences always normalize to triple backticks (` ``` `) with language hints preserved.

#### Data Model Snapshot

| Entity | Description |
| :----- | :---------- |
| `NormalizedDocument` | Canonical Markdown representation. |
| `DiffLine` | Describes a single line in the unified diff. |
| `InlineDiffSegment` | Tracks each inline token change. |

#### Example Configuration

```toml
[diff]
line_similarity = 0.6
inline = "auto"
```

## Frequently Asked Questions

**Q:** What happens to GitHub-specific Markdown extensions?  
**A:** The normalizer keeps their textual form but does not attempt to emulate rendering semantics.

**Q:** Is streaming supported for large documents?  
**A:** Not in v1. The API expects inputs that fit in memory.

## Appendix

- [mddiff.dev/guides](https://example.com) — onboarding tutorials.  
- [mddiff.dev/changelog](https://example.com) — release notes and upcoming milestones.

