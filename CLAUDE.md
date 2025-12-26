# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a repository for the book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies. The book is written in markdown with each chapter in its own directory.

## Repository Structure

```
book_agentic_patterns/
├── chapters/
│   ├── 01_foundations/
│   │   ├── chapter.md          # Chapter content
│   │   └── img/               # Images for this chapter
│   ├── 02_pattern_name/
│   │   ├── chapter.md
│   │   └── img/
│   └── 03_pattern_name/
│       ├── chapter.md
│       └── img/
├── src/
│   ├── 01_foundations/       # Code examples for chapter 1
│   │   ├── example_01.py
│   │   └── example_02.py
│   ├── 02_pattern_name/       # Code examples for chapter 2
│   └── shared/                # Shared utilities across chapters
├── scripts/                   # Build, validation, lint scripts
└── tests/                     # Tests for code examples
    ├── test_01.py
    ├── test_02.py
    └── test_03.py
```

## Conventions

**Chapter directories**: All chapters under `chapters/` directory. Name them `XX_descriptive_name` where XX is zero-padded (01, 02, etc.). Each contains only `chapter.md` with the chapter text in markdown format.

**Code organization**: All code in `src/`. Mirror chapter structure with `src/XX_descriptive_name/` directories using chapter numbers. Shared utilities go in `src/shared/`. Follow global Python conventions (type hints, pathlib, etc.).

**Images**: Stored within each chapter directory in an `img/` subdirectory. Reference from markdown using relative paths: `![Description](img/diagram.png)`. This keeps images co-located with their corresponding chapter content.

**Tests**: In `tests/` directory at root. Name test files to match chapters (`test_01.py`, `test_02.py`). Use standard Python unittest framework. Run via `scripts/test.sh`.

**Dependencies**: Single `pyproject.toml` or `requirements.txt` at root for all code examples. All chapters share the same dependency environment.

**Code imports**: When code in `src/XX/` imports from `src/shared/`, ensure PYTHONPATH is set correctly or use relative imports. Consider adding `src/` to PYTHONPATH in scripts.

**Chapter numbering**: Using sequential numbers (01, 02, 03) makes reordering hard. If you plan to insert chapters later, consider leaving gaps (01, 05, 10, etc.) or non-sequential numbering.

**Image optimization**: Use compressed PNGs or SVGs for diagrams to keep repository size manageable. Large images bloat git history permanently.

**References**: All refereences and citations should be included in a `references.md` file