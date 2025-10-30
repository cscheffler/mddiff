from __future__ import annotations

import time

import pytest

from mddiff import diff


def _build_documents() -> tuple[str, str]:
    left_lines: list[str] = ["# Benchmark Document\n", "\n"]
    right_lines: list[str] = ["# Benchmark Document\n", "\n"]

    for section in range(1, 151):
        header = f"## Section {section}\n"
        left_lines.append(header)
        right_lines.append(header if section % 7 else f"## Section {section} Update\n")

        for item in range(1, 31):
            left_lines.append(f"- Bullet {section}.{item}\n")
            bullet = f"- Bullet {section}.{item}\n"
            if item % 5 == 0 and section % 3 == 0:
                bullet = bullet.rstrip("\n") + " (adjusted)\n"
            right_lines.append(bullet)

        left_lines.append("\n")
        right_lines.append("\n")

        summary_left = f"Summary {section}: steady performance with baseline metrics.\n"
        left_lines.append(summary_left)
        right_summary = (
            summary_left
            if section % 4
            else f"Summary {section}: performance updated after refactor with audit trail.\n"
        )
        right_lines.append(right_summary)

        left_lines.append(
            "Paragraph "
            + str(section)
            + ": "
            + "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 2
            + "\n"
        )
        right_lines.append(
            "Paragraph "
            + str(section)
            + ": "
            + "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            + ("Vestibulum efficitur nisl. " if section % 9 == 0 else "Suspendisse varius. ")
            + "\n"
        )

        left_lines.append("\n")
        right_lines.append("\n")

        left_lines.extend([
            "| Metric | Value |\n",
            "| --- | --- |\n",
            f"| throughput | {section * 8} |\n",
            "\n",
        ])
        right_lines.extend([
            "| Metric | Value |\n",
            "| --- | --- |\n",
            f"| throughput | {section * (8 + (section % 5))} |\n",
        ])
        if section % 6 == 0:
            right_lines.append(f"| latency | {section * 3} |\n")
        right_lines.append("\n")

    left_text = "".join(left_lines)
    right_text = "".join(right_lines)
    return left_text, right_text


@pytest.mark.performance
def test_diff_completes_within_one_second_for_100kb_documents():
    left_text, right_text = _build_documents()

    assert len(left_text) >= 100_000
    assert len(right_text) >= 100_000

    start = time.perf_counter()
    result = diff(left_text, right_text)
    elapsed = time.perf_counter() - start

    assert result.has_changes
    assert elapsed < 1.0, f"Diff took {elapsed:.3f}s, expected < 1.0s"
