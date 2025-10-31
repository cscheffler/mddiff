from __future__ import annotations

from pathlib import Path

import importlib
import sys

import pytest

import mddiff.cli as cli


@pytest.fixture
def sample_files(tmp_path: Path) -> tuple[Path, Path]:
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    left.write_text("# Title\n\nValue one\n", encoding="utf-8")
    right.write_text("# Title\n\nValue two\n", encoding="utf-8")
    return left, right


def test_cli_main_reports_changes(capsys, sample_files: tuple[Path, Path]) -> None:
    left, right = sample_files
    exit_code = cli.main([str(left), str(right)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Value" in captured.out
    assert captured.err == ""


def test_cli_main_no_changes(capsys, tmp_path: Path) -> None:
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    text = "Context line\n"
    left.write_text(text, encoding="utf-8")
    right.write_text(text, encoding="utf-8")

    exit_code = cli.main([str(left), str(right)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_cli_main_html_unified(capsys, sample_files: tuple[Path, Path]) -> None:
    left, right = sample_files
    exit_code = cli.main([
        "--context",
        "0",
        "--format",
        "html-unified",
        str(left),
        str(right),
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "mddiff-diff--layout-unified" in captured.out
    assert captured.err == ""


def test_cli_main_rejects_double_stdin() -> None:
    with pytest.raises(SystemExit):
        cli.main(["-", "-"])


def test_import_reload_covered() -> None:
    module = importlib.reload(sys.modules["mddiff"])
    # Ensure exported symbols remain available after reload
    assert hasattr(module, "diff")

def test_cli_main_html_split_with_inline_options(capsys, sample_files):
    left, right = sample_files
    exit_code = cli.main([
        "--inline-min-real-quick",
        "0.1",
        "--inline-min-quick",
        "0.2",
        "--inline-min-ratio",
        "0.25",
        "--format",
        "html-split",
        str(left),
        str(right),
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "mddiff-diff--layout-split" in captured.out
    assert captured.err == ""


def test_build_inline_config_branches():
    parser = cli._build_parser()
    args = parser.parse_args([
        "--inline-min-real-quick",
        "0.3",
        "--inline-min-quick",
        "0.4",
        "--inline-min-ratio",
        "0.5",
        "file_a",
        "file_b",
    ])
    config = cli._build_inline_config(args)
    assert config is not None
    assert config.min_real_quick_ratio == 0.3
    assert config.min_quick_ratio == 0.4
    assert config.min_ratio == 0.5


def test_resolve_version_smoke(monkeypatch):
    import importlib.metadata as metadata

    class DummyError(Exception):
        pass

    monkeypatch.setattr(metadata, "version", lambda name: "9.9.9")
    monkeypatch.setattr(metadata, "PackageNotFoundError", DummyError)
    assert cli._resolve_version() == "9.9.9"



def test_resolve_version_fallback(monkeypatch):
    import importlib.metadata as metadata

    class DummyError(Exception):
        pass

    def raise_error(name: str) -> str:
        raise DummyError()

    monkeypatch.setattr(metadata, "version", raise_error)
    monkeypatch.setattr(metadata, "PackageNotFoundError", DummyError)
    assert cli._resolve_version() == "0.0.0"
