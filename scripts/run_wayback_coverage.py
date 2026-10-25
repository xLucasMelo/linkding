"""Run reproducible before/after coverage for the Wayback URL helper.

Usage (from the repository root):
    .venv/Scripts/python.exe scripts/run_wayback_coverage.py baseline
    .venv/Scripts/python.exe scripts/run_wayback_coverage.py new
    .venv/Scripts/python.exe scripts/run_wayback_coverage.py combined
"""

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW_TESTS = "bookmarks/tests/test_wayback.py"
OUTPUT = ROOT / "output" / "relatorio2-wayback"


class Tee:
    def __init__(self, console, log):
        self.console = console
        self.log = log

    def write(self, text):
        self.console.write(text)
        self.log.write(text)
        self.log.flush()
        return len(text)

    def flush(self):
        self.console.flush()
        self.log.flush()

    def isatty(self):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("baseline", "new", "combined"))
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ["DJANGO_SETTINGS_MODULE"] = "bookmarks.settings.dev"
    OUTPUT.mkdir(parents=True, exist_ok=True)

    import coverage
    import django
    import pytest
    from django.conf import settings

    # Test-process-only infrastructure; no project configuration or user DB changes.
    runtime = tempfile.TemporaryDirectory(
        prefix="linkding-wayback-", ignore_cleanup_errors=True
    )
    settings.HUEY = {
        **settings.HUEY,
        "filename": str(Path(runtime.name) / "tasks.sqlite3"),
    }
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.DATABASES["default"]["TEST"] = {"NAME": ":memory:"}

    cov = coverage.Coverage(
        branch=True,
        source=["bookmarks.services.wayback"],
        config_file=False,
        data_file=str(OUTPUT / f"{args.phase}.coverage"),
    )
    suite = [NEW_TESTS] if args.phase == "new" else ["bookmarks/tests"]
    pytest_args = suite + ["-q", "--tb=short", "--color=no"]
    if args.phase == "baseline":
        pytest_args.append(f"--ignore={NEW_TESTS}")

    log_file = OUTPUT / f"{args.phase}-tests.txt"
    with log_file.open("w", encoding="utf-8") as log:
        original_stdout, original_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = Tee(sys.stdout, log), Tee(sys.stderr, log)
        try:
            print(f"Phase: {args.phase}; pytest {' '.join(pytest_args)}")
            cov.start()
            django.setup()
            result = int(pytest.main(pytest_args))
            cov.stop()
            cov.save()
            cov.json_report(outfile=str(OUTPUT / f"{args.phase}-coverage.json"))
            cov.html_report(directory=str(OUTPUT / f"{args.phase}-html"))
            cov.report(show_missing=True)
        finally:
            sys.stdout, sys.stderr = original_stdout, original_stderr

    metadata = {
        "phase": args.phase,
        "exit_code": result,
        "pytest_args": pytest_args,
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "python": sys.version,
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("Django", "coverage", "pytest", "pytest-django")
        },
        "test_settings": {
            "huey": "SqliteHuey (temporary file)",
            "background_tasks_disabled": settings.LD_DISABLE_BACKGROUND_TASKS,
            "test_database": ":memory:",
            "password_hasher": "MD5PasswordHasher (tests only)",
        },
    }
    (OUTPUT / f"{args.phase}-metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    sys.exit(main())
