---
name: check_chapters.consistency
description: Check chapters consistency betweend chapters.md and chapters/*/chapter.md
---

See the *.md files and make sure that all the "chapter.md" files from each chapter are up to date (not missing entries)
Also make sure 'chapters.md' is up to date (not missing entries)

The order in each chapter should be:
- Introduction
- Historical Perspectives (if present): All historical perspectives from the chapter should be in a single "Historical Perspectives" section at the start of the chapter
- Main sections 
- Hands-on intro (if present)
- Hands-on sections (if present)
- References: All references from the chapter should be in a single "References" section at the end of the chapter

In chapters.md, each chapter should have:
- One line description of key topics covered in the chapter (read the chapter *.md files to extract this information)
- One line for each sections (including hands-on sections) with a one-liner description of key topic/s is covered in each section.
- Make sure that all the sections listed in chapters.md are actually present in the corresponding chapter.md files, and that there are no extra sections in the chapter.md files that are not listed in chapters.md.

Keep in mind some chapters are NOT finished yet. Flag them as "TODO" in chapters.md, and make sure that the corresponding chapter.md files are consistent with that (i.e. they should be missing some sections, or have some sections marked as TODO).

READ FILES MANUALLY, DO NOT IMPLEMENT ANY CODE OR RUN ANY COMMANDS.
