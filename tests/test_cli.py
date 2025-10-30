from __future__ import annotations

import os
import subprocess
import sys


def _run_cli(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(os.path.join(os.getcwd(), "src")),
            *(env.get("PYTHONPATH", "").split(os.pathsep) if env.get("PYTHONPATH") else []),
        ]
    ).rstrip(os.pathsep)
    return subprocess.run(
        [sys.executable, "-m", "mddiff.cli", *args],
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_cli_no_changes_returns_zero(tmp_path):
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    content = "# Title\n\nSame content.\n"
    left.write_text(content, encoding="utf-8")
    right.write_text(content, encoding="utf-8")

    result = _run_cli(str(left), str(right))

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_cli_outputs_diff_and_nonzero_exit(tmp_path):
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    left.write_text("Value one\n", encoding="utf-8")
    right.write_text("Value two\n", encoding="utf-8")

    result = _run_cli(str(left), str(right))

    assert result.returncode == 1
    assert result.stderr == ""
    assert result.stdout == "-Value [-one-]\n+Value {+two+}\n"


def test_cli_inline_config_flags_disable_inline_segments(tmp_path):
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    left.write_text("Value one\n", encoding="utf-8")
    right.write_text("Value two\n", encoding="utf-8")

    result = _run_cli("--inline-min-ratio", "0.9", str(left), str(right))

    assert result.returncode == 1
    assert result.stderr == ""
    assert result.stdout == "-Value one\n+Value two\n"


def test_cli_context_flag_limits_output(tmp_path):
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    left.write_text("- alpha\n- beta\n- charlie\n", encoding="utf-8")
    right.write_text("- alpha\n- beta two\n- charlie\n", encoding="utf-8")

    result = _run_cli("--context", "0", str(left), str(right))

    assert result.returncode == 1
    assert result.stderr == ""
    assert result.stdout.startswith("@@ -2,1 +2,1 @@\n")
    assert "-- beta\n" in result.stdout


def test_cli_rejects_double_stdin():
    result = _run_cli("-", "-", input_text="left\n")

    assert result.returncode != 0
    assert result.stdout == ""
    assert "Cannot read both inputs" in result.stderr
