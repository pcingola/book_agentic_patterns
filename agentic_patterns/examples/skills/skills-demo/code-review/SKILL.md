---
name: code-review
description: Review code for quality, bugs, and security issues.
compatibility: Works with Python, JavaScript, and TypeScript files.
---

# Code Review

## When to use this skill

Use this skill when asked to review, analyze, or check code for issues. This includes security audits, bug detection, and code quality assessments.

## How to use

Run the bundled analysis script to scan for common issues:

```
python scripts/analyze.py <file>          # analyze a file
python scripts/analyze.py -c '<code>'     # analyze inline code
```

Use the script output as the basis for your review, then add your own observations about logic and design.

## What to look for

When reviewing code, check for:
- Security vulnerabilities (eval, exec, SQL injection, XSS)
- Error handling gaps
- Resource leaks
- Logic errors

## Output

Provide a clear list of issues found, categorized by severity (CRITICAL, WARNING, INFO).
