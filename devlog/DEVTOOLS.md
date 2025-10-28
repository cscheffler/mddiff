# Devtools Ideas (2025-02-14)

- Add a tiny CLI helper that runs targeted pytest subsets (`normalize`, `regression`, or individual fixtures) to avoid manual filtering each time.
- Integrate a Markdown-focused linter (e.g., remark-lint) into the pipeline to flag escape anomalies before they hit normalization.
- Introduce a snapshot-based regression harness that serializes normalized output for each fixture and diff-checks changes in PRs.
- Consider wiring up watchman/entr to auto-run normalization tests on file changes for faster inner-loop feedback.
