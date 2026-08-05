#!/usr/bin/env python
"""Run full backend test suite."""

import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no"],
    capture_output=True,
    text=True,
    cwd=r"c:\Users\KNP LIBRARY\Downloads\Nebula Search\Nebula-search-engine--main\backend"
)

# Save output
with open("full_test_output.txt", "w", encoding="utf-8") as f:
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\n\nReturn code: {result.returncode}\n")

# Print summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)

# Count passed/failed
stdout_lines = result.stdout.split('\n')
for line in stdout_lines:
    if 'passed' in line.lower() or 'failed' in line.lower():
        print(line)

print("\n" + "=" * 80)
print(f"Return code: {result.returncode}")
print("=" * 80)

print("\nOutput saved to full_test_output.txt")
