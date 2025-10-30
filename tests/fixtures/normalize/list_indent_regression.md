# List Indentation Regression

Synthetic Markdown that reproduces inconsistent list spacing:

- Top-level bullet A.
- Top-level bullet B.
  + Nested with two spaces.
    - Sub-bullet using four spaces.
        - Deep bullet indented eight spaces.
    - Another sub-bullet with mixed spacing.
  + Second mixed list item.
- Top-level bullet C.

## Ordered Sequence

1. Start point.
1) Alternate numbering with parenthesis.
   3. Third item indented by three spaces.

## Mixed Content Block

* Highlights section.
* Logbook entries.
  + Follow-up tasks:
     - Normalize the indentation.
     - Ensure cached output is idempotent.
     - Verify four-space nesting.
  + Tracking notes
    - Bullet written with a tab	character.
    - Bullet with two spaces.
- Final summary bullet.

