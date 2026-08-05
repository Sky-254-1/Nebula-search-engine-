#!/usr/bin/env python
"""Run tests and capture output."""

import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_search_unified.py", "-v"],
    capture_output=True,
    text=True,
    cwd=r"c:\Users\KNP LIBRARY\Downloads\Nebula Search\Nebula-search-engine--main\backend"
)

print(result.stdout)
print(result.stderr)
print(f"Return code: {result.returncode}")
