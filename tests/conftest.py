from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest
from trace import Trace, _find_executable_linenos

try:  # pragma: no cover - optional dependency in sandbox
    import coverage as coverage_lib
except ImportError:  # pragma: no cover
    coverage_lib = None


@dataclass
class _FileCoverage:
    path: Path
    executed: int
    total: int
    coverage: float
    missing: list[int]


class _TraceCoveragePlugin:
    def __init__(self, config: pytest.Config) -> None:
        self._config = config
        self._targets: list[str] = list(config.getoption("--cov") or [])
        self._reports: list[str] = list(config.getoption("--cov-report") or [])
        self._fail_under = config.getoption("--cov-fail-under")
        self._tracer: Trace | None = None
        self._cov: "coverage_lib.Coverage" | None = None  # type: ignore[name-defined]
        self._summary: dict[str, object] | None = None
        self._target_dirs: list[Path] = []

    # pytest hooks -----------------------------------------------------
    def pytest_sessionstart(self, session: pytest.Session) -> None:  # noqa: D401
        """Start tracing as soon as the session begins."""
        if not self._targets:
            return
        self._target_dirs = self._collect_target_dirs()
        if coverage_lib is not None:
            self._cov = coverage_lib.Coverage(
                source=[str(path) for path in self._target_dirs] or None,
            )
            self._cov.start()
        else:
            ignoredirs = {sys.prefix, sys.exec_prefix}
            self._tracer = Trace(count=True, trace=False, ignoredirs=ignoredirs)
            sys.settrace(self._tracer.globaltrace)
            threading.settrace(self._tracer.globaltrace)
        self._reload_targets()

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:  # noqa: D401
        """Stop tracing and evaluate coverage on session finish."""
        if self._cov is not None:
            self._cov.stop()
            self._cov.save()
            if "html" in self._reports:
                self._cov.html_report(directory="htmlcov")
            self._summary = self._build_coverage_summary(self._cov)
        elif self._tracer is not None:
            sys.settrace(None)
            threading.settrace(None)
            results = self._tracer.results()
            self._summary = self._build_summary(results)
        else:
            return

        session.config._trace_cov_summary = self._summary
        if (
            self._fail_under is not None
            and self._summary["total_lines"]
            and self._summary["percent"] + 1e-9 < self._fail_under
        ):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED

    def pytest_terminal_summary(self, terminalreporter, exitstatus: int) -> None:  # noqa: D401
        """Emit a simple terminal summary when tracing ran."""
        summary = self._summary
        if not summary:
            return
        terminalreporter.write_sep(
            "-",
            f"coverage: {summary['percent']:.1f}% of {summary['total_lines']} lines",
        )
        if "term-missing" in self._reports:
            for info in summary["files"]:
                file_info: _FileCoverage = info
                terminalreporter.write_line(
                    f"{file_info.coverage:6.1f}% {file_info.executed:4d}/{file_info.total:4d} {file_info.path}"
                )
                if file_info.missing:
                    missing = ",".join(str(num) for num in file_info.missing)
                    terminalreporter.write_line(f"    Missing: {missing}")

    # helper methods ---------------------------------------------------
    def _build_summary(self, results) -> dict[str, object]:
        target_dirs = self._target_dirs or self._collect_target_dirs()
        all_files = self._discover_python_files(target_dirs)
        hits_map = self._collect_hits(results)

        file_coverages: list[_FileCoverage] = []
        total_executed = 0
        total_lines = 0

        for path in sorted(all_files):
            executable = _find_executable_linenos(str(path))
            if not executable:
                continue
            executable_lines = {ln for ln in executable if isinstance(ln, int) and ln > 0}
            if not executable_lines:
                continue
            hits = hits_map.get(path, set())
            executed_lines = {ln for ln in hits if isinstance(ln, int) and ln > 0}
            executed = len(executable_lines & executed_lines)
            missing = sorted(ln for ln in executable_lines - executed_lines)
            coverage = (executed / len(executable_lines)) * 100.0
            total_executed += executed
            total_lines += len(executable_lines)
            file_coverages.append(
                _FileCoverage(
                    path=path,
                    executed=executed,
                    total=len(executable_lines),
                    coverage=coverage,
                    missing=missing,
                )
            )

        percent = (total_executed / total_lines * 100.0) if total_lines else 100.0
        return {
            "files": file_coverages,
            "total_lines": total_lines,
            "executed": total_executed,
            "percent": percent,
        }

    def _build_coverage_summary(self, cov) -> dict[str, object]:
        file_coverages: list[_FileCoverage] = []
        total_lines = 0
        total_executed = 0

        data = cov.get_data()
        for filename in data.measured_files():
            path = Path(filename)
            if self._target_dirs and not any(_is_relative_to(path, root) for root in self._target_dirs):
                continue
            try:
                _, statements, excluded, missing, _ = cov.analysis2(filename)
            except Exception:  # pragma: no cover - defensive fallback
                continue

            executable = {ln for ln in statements if isinstance(ln, int) and ln > 0}
            excluded_lines = {ln for ln in excluded if isinstance(ln, int) and ln > 0}
            missing_lines = {ln for ln in missing if isinstance(ln, int) and ln > 0}
            executable -= excluded_lines
            if not executable:
                continue

            executed = executable - missing_lines
            total_lines += len(executable)
            total_executed += len(executed)
            file_coverages.append(
                _FileCoverage(
                    path=path,
                    executed=len(executed),
                    total=len(executable),
                    coverage=(len(executed) / len(executable)) * 100.0,
                    missing=sorted(executable - executed),
                )
            )

        percent = (total_executed / total_lines * 100.0) if total_lines else 100.0
        return {
            "files": file_coverages,
            "total_lines": total_lines,
            "executed": total_executed,
            "percent": percent,
        }

    def _collect_target_dirs(self) -> list[Path]:
        dirs: list[Path] = []
        for target in self._targets:
            spec = importlib.util.find_spec(target)
            if spec is None or spec.origin is None:
                continue
            path = Path(spec.origin).resolve()
            dirs.append(path.parent if path.name == "__init__.py" else path.parent)
        return dirs

    def _reload_targets(self) -> None:
        for target in self._targets:
            try:
                module = importlib.import_module(target)
            except ImportError:
                continue
            importlib.reload(module)

    def _discover_python_files(self, dirs: Iterable[Path]) -> set[Path]:
        files: set[Path] = set()
        for directory in dirs:
            if not directory.exists():
                continue
            for path in directory.rglob("*.py"):
                files.add(path.resolve())
        return files

    def _collect_hits(self, results) -> dict[Path, set[int]]:
        hits_map: dict[Path, set[int]] = {}
        for (filename, lineno), count in results.counts.items():
            if count <= 0 or not isinstance(lineno, int) or lineno <= 0:
                continue
            path = Path(filename)
            if path.suffix != ".py":
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            linenos = hits_map.setdefault(resolved, set())
            linenos.add(int(lineno))
        return hits_map

def pytest_addoption(parser):  # noqa: D401
    """Register coverage command-line options."""
    if coverage_lib is None:
        group = parser.getgroup("coverage")
        group.addoption("--cov", action="append", default=[], help="Modules to measure coverage for.")
        group.addoption(
            "--cov-report",
            action="append",
            default=[],
            help="Coverage report types (supports 'term' and 'term-missing'/'html').",
        )
        group.addoption(
            "--cov-fail-under",
            action="store",
            type=float,
            default=None,
            help="Fail the test session if total coverage is below this percentage.",
        )


def pytest_configure(config):  # noqa: D401
    """Activate the trace-based coverage plugin when --cov is requested."""
    if config.getoption("--cov") and coverage_lib is None:
        plugin = _TraceCoveragePlugin(config)
        config._trace_cov_plugin = plugin  # type: ignore[attr-defined]
        config.pluginmanager.register(plugin, "trace-coverage-plugin")


def pytest_unconfigure(config):  # noqa: D401
    """Unregister the trace-based coverage plugin."""
    plugin = getattr(config, "_trace_cov_plugin", None)
    if plugin is not None:
        config.pluginmanager.unregister(plugin)
        delattr(config, "_trace_cov_plugin")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:  # noqa: D401
    """Skip performance tests whenever coverage measurement is requested."""
    cov_requested = bool(config.getoption("--cov", default=None))
    if not cov_requested:
        return
    skip_marker = pytest.mark.skip(reason="Performance tests skipped under coverage measurement")
    for item in items:
        if item.get_closest_marker("performance"):
            item.add_marker(skip_marker)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
