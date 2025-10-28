# Markdown diff library

## Project description

We'll build a Markdown diff library in Python.

Its purpose is to take any two Markdown texts, of arbitrary length, normalize them, compare them, and produce one, unified diff view on the two texts.

The first step is to normalize both Markdown texts. If there is an existing, well-known Python library for doing the normalization, use that. Otherwise, create one. The goal of normalization is that any two Markdown texts that would render the same way should result in the name normalized form. For example, a paragraph over multiple lines must be on one line. Any acceptable number of spaces before a bullet should be normalized to the same number of spaces. All bullets should use the same character the delimit them as bullets, all numbers in a numbered list should be converted to "1.", etc. The normalization step will enable the diff algorithm to be more efficient.

When comparing the two texts, we want to identified matching or nearly matching lines first, while also marking which lines got added or removed wholesale. We then want to determine, within each modified line, which words got added, removed, or replaced. Perhaps GNU wdiff already does this? Investigate.

The library should produce a data structure that can be iterated over to get each line from the unified diff view, where each line is marked as unchanged, inserted, deleted, or edited. Each edited line contains an iterable over sequences of words/symbols, each marked as unchanged, inserted, deleted, or edited.

There should also be functionality to print this data structure out as text, showing which lines and words were changed.

## What's done

- Normalization MVP implemented with escape-aware inline handling and regression fixtures.

## What's left

- Implement diff engine: line-level matching, inline token diff, data models, rendering.
- Build CLI wrapper and package scaffolding per SDD (CLI entry point, pyproject configuration).
- Add broader regression corpus, performance checks, and documentation per SDD milestones.
