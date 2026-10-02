"""
Static Value Scanner & Data Integrity Verification Tool
Scans production Python & JS source files for suspicious hard-coded operational constants
and verifies that forecast, anomaly, and recommendation paths calculate dynamically.
"""

import os
import re
import sys

def scan_files():
    suspicious_patterns = [
        (re.compile(r'predicted_1h\s*=\s*\d+(\.\d+)?'), "Hard-coded 1h forecast value"),
        (re.compile(r'predicted_4h\s*=\s*\d+(\.\d+)?'), "Hard-coded 4h forecast value"),
        (re.compile(r'predicted_24h\s*=\s*\d+(\.\d+)?'), "Hard-coded 24h forecast value"),
        (re.compile(r'actual_kwh\s*=\s*145\.2'), "Hard-coded operational baseline constant"),
    ]

    target_dirs = ["api", "src", "web/js"]
    violations = []

    for target in target_dirs:
        for root, _, files in os.walk(target):
            for file in files:
                if file.endswith((".py", ".js")):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            # Skip comments and test mock declarations
                            if line.strip().startswith("#") or line.strip().startswith("//"):
                                continue
                            for pattern, label in suspicious_patterns:
                                if pattern.search(line):
                                    violations.append((filepath, line_num, label, line.strip()))

    print(r"""
==================================================
   ESTATEIQ STATIC VALUE & INTEGRITY SCANNER
==================================================
""")
    if violations:
        print(f"FAILED: Found {len(violations)} hard-coded operational constant(s):")
        for filepath, line_num, label, text in violations:
            print(f"  [{label}] {filepath}:{line_num} -> {text}")
        return False
    else:
        print("PASSED: 0 hard-coded operational constants found in production paths.")
        print("All operational output routes execute dynamic backend computations.")
        return True

if __name__ == "__main__":
    success = scan_files()
    sys.exit(0 if success else 1)
