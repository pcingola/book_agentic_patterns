"""Static analysis script for code review."""

import sys


def analyze(code: str) -> list[str]:
    """Scan code for common security issues."""
    issues = []
    if "eval(" in code:
        issues.append(
            "CRITICAL: eval() with user input allows arbitrary code execution"
        )
    if "exec(" in code:
        issues.append(
            "CRITICAL: exec() with user input allows arbitrary code execution"
        )
    if "os.system(" in code:
        issues.append("WARNING: os.system() is vulnerable to command injection")
    if not issues:
        issues.append("No critical issues found")
    return issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <file> | -c '<code>'")
        sys.exit(1)
    if sys.argv[1] == "-c":
        code = " ".join(sys.argv[2:])
    else:
        with open(sys.argv[1]) as f:
            code = f.read()
    for issue in analyze(code):
        print(issue)
