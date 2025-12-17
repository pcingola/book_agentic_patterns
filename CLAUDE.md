# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a repository for the book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies. The book is written in markdown with each chapter in its own directory.

## Repository Structure

```
book_agentic_patterns/
├── chapter_01_pattern_name/
│   └── README.md              # Chapter content
├── chapter_02_pattern_name/
│   └── README.md
├── src/
│   ├── chapter_01/            # Code examples for chapter 1
│   │   ├── example_01.py
│   │   └── example_02.py
│   ├── chapter_02/            # Code examples for chapter 2
│   └── shared/                # Shared utilities across chapters
├── images/                    # All images for the book
│   ├── chapter_01/
│   └── chapter_02/
├── scripts/                   # Build, validation, lint scripts
└── tests/                     # Tests for code examples
    ├── test_chapter_01.py
    └── test_chapter_02.py
```

## Conventions

**Chapter directories**: Name them `chapter_XX_descriptive_name` where XX is zero-padded (01, 02, etc.). Each contains only `README.md` with the chapter text.

**Code organization**: All code in `src/`. Mirror chapter structure with `src/chapter_XX/` directories. Shared utilities go in `src/shared/`. Follow global Python conventions (type hints, pathlib, etc.).

**Images**: Centralized in `images/` directory, organized by chapter (`images/chapter_01/`, `images/chapter_02/`). Reference from markdown using relative paths: `![Description](../images/chapter_01/diagram.png)`.

**Tests**: In `tests/` directory at root. Name test files to match chapters (`test_chapter_01.py`). Use standard Python unittest framework. Run via `scripts/test.sh`.

**Dependencies**: Single `pyproject.toml` or `requirements.txt` at root for all code examples. All chapters share the same dependency environment.

## Things to Watch Out For

**Markdown image paths**: From `chapter_XX/README.md`, images are referenced as `../images/chapter_XX/filename.png`. Double-check relative paths work when viewing on GitHub.

**Code imports**: When code in `src/chapter_XX/` imports from `src/shared/`, ensure PYTHONPATH is set correctly or use relative imports. Consider adding `src/` to PYTHONPATH in scripts.

**Runnable examples**: All code in `src/` should be executable. Include setup instructions if API keys or configuration needed. Don't leave incomplete code snippets that won't run.

**Chapter numbering**: Using `chapter_01`, `chapter_02` makes reordering hard. If you plan to insert chapters later, consider non-sequential numbering or leaving gaps (01, 05, 10, etc.).

**Image optimization**: Use compressed PNGs or SVGs for diagrams to keep repository size manageable. Large images bloat git history permanently.

**Cross-references**: When linking between chapters, use relative markdown links: `[See Chapter 2](../chapter_02_pattern_name/README.md)`.

**Code-to-chapter mapping**: Keep `src/chapter_XX/` directory names aligned with corresponding `chapter_XX/` content directories for clarity.
