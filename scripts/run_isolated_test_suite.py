from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def main() -> int:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(TESTS)
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    total = 0
    failures = []
    files = sorted(TESTS.glob("test_*.py"))
    for path in files:
        module = f"tests.{path.stem}"
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", module, "-q"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        output = f"{completed.stdout}\n{completed.stderr}"
        match = re.search(r"Ran\s+(\d+)\s+tests?", output)
        count = int(match.group(1)) if match else 0
        total += count
        if completed.returncode:
            failures.append(path.name)
            print(f"[FAIL] {path.name}")
            print(output.strip())
        else:
            print(f"[PASS] {path.name}: {count}")
    print(f"ISOLATED_SUITE_FILES={len(files)}")
    print(f"ISOLATED_SUITE_TESTS={total}")
    print(f"ISOLATED_SUITE_FAILURES={len(failures)}")
    if failures:
        print("FAILED_FILES=" + ",".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
