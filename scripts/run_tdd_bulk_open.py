"""Record real TDD stages for bulk URL opening, without external browser actions.

Usage: python scripts/run_tdd_bulk_open.py cycle9-red
       python scripts/run_tdd_bulk_open.py final --suite regression
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "tdd-cycles-9-10"
TEST_FILES = [
    "bookmarks/tests/test_bookmark_action_view.py",
    "bookmarks/tests/test_bookmark_index_view.py",
    "bookmarks/tests/test_bookmark_archived_view.py",
]
TRACKED_SOURCES = [
    "bookmarks/frontend/components/bookmark-page.js",
    "bookmarks/frontend/tests/bookmark-page.test.cjs",
    "bookmarks/templates/bookmarks/bulk_edit_bar.html",
    *TEST_FILES,
]


def run_django(suite):
    sys.path.insert(0, str(ROOT))
    os.environ["DJANGO_SETTINGS_MODULE"] = "bookmarks.settings.dev"
    import django
    import pytest
    from django.conf import settings

    with tempfile.TemporaryDirectory(prefix="linkding-tdd-") as temporary:
        # Changes only this isolated test process, never production settings.
        settings.HUEY = {**settings.HUEY, "filename": str(Path(temporary) / "huey.db")}
        settings.DATABASES["default"]["TEST"] = {"NAME": ":memory:"}
        settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
        django.setup()
        args = [*TEST_FILES, "-q", "--tb=short", "--color=no"]
        if suite == "menu":
            args.extend(["-k", "allowed_bulk_actions"])
        return int(pytest.main(args))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase")
    parser.add_argument("--suite", choices=("menu", "regression"), default="menu")
    parser.add_argument("--python-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.python_child:
        return run_django(args.suite)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required to run the component unit tests")
    commands = {
        "frontend": [
            node,
            "--experimental-vm-modules",
            "--test-reporter=tap",
            "--test",
            "bookmarks/frontend/tests/bookmark-page.test.cjs",
        ],
        "django": [
            sys.executable,
            str(Path(__file__).resolve()),
            args.phase,
            "--python-child",
            "--suite",
            args.suite,
        ],
    }
    metadata = {
        "phase": args.phase,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": sys.version,
        "node": subprocess.check_output([node, "--version"], text=True).strip(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("Django", "pytest", "pytest-django")
        },
        "suite": args.suite,
        "test_settings": "SQLite in-memory; temporary Huey file; MD5 hasher (test process only)",
        "log_note": "Actual subprocess output; repository-root paths replaced with <repo>.",
        "sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in TRACKED_SOURCES
        },
        "exit_codes": {},
    }
    for name, command in commands.items():
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        log = (result.stdout + result.stderr).replace(str(ROOT), "<repo>")
        (OUTPUT / f"{args.phase}-{name}.txt").write_text(log, encoding="utf-8")
        metadata["exit_codes"][name] = result.returncode
        print(f"{args.phase} / {name}: exit {result.returncode}")
        print(log)
    (OUTPUT / f"{args.phase}-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return int(any(metadata["exit_codes"].values()))


if __name__ == "__main__":
    sys.exit(main())
