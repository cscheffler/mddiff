"""Release checklist for mddiff."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run release readiness checks.")
    parser.add_argument(
        "--tests",
        action="store_true",
        help="Run pytest suite (default behavior).",
    )
    parser.add_argument(
        "--no-tests",
        dest="tests",
        action="store_false",
        help="Skip pytest run.",
    )
    parser.set_defaults(tests=True)
    args = parser.parse_args(argv)

    ok = True

    ok &= _check_readme_has_cli_section()
    ok &= _check_pyproject_metadata()

    if args.tests:
        ok &= _run_pytest()

    return 0 if ok else 1


def _check_readme_has_cli_section() -> bool:
    readme = Path("README.md")
    if not readme.exists():
        _fail("README.md is missing")
        return False
    text = readme.read_text(encoding="utf-8")
    required_phrases = [
        "## Installation",
        "## CLI Usage",
        "InlineDiffConfig",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in text]
    if missing:
        _fail(f"README.md missing sections: {', '.join(missing)}")
        return False
    _ok("README.md includes installation, CLI, and library usage sections")
    return True


def _check_pyproject_metadata() -> bool:
    path = Path("pyproject.toml")
    if not path.exists():
        _fail("pyproject.toml is missing")
        return False
    data = _load_toml(path)
    project = data.get("project", {})

    required_fields = ["name", "version", "description", "readme", "requires-python"]
    missing = [field for field in required_fields if field not in project]
    if missing:
        _fail(f"pyproject.toml missing project metadata fields: {', '.join(missing)}")
        return False

    scripts = project.get("scripts", {})
    if "mddiff" not in scripts:
        _fail("pyproject.toml missing 'mddiff' console script entry")
        return False

    _ok("pyproject.toml metadata and console script look good")
    return True


def _run_pytest() -> bool:
    _info("Running pytest...")
    result = subprocess.run([sys.executable, "-m", "pytest"], check=False)
    if result.returncode != 0:
        _fail("pytest reported failures")
        return False
    _ok("pytest passed")
    return True


def _load_toml(path: Path) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _ok(message: str) -> None:
    print(f"[ok] {message}")


def _fail(message: str) -> None:
    print(f"[fail] {message}")


def _info(message: str) -> None:
    print(f"[info] {message}")


if __name__ == "__main__":
    raise SystemExit(main())

