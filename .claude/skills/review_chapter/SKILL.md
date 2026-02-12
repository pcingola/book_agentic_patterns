---
name: review_chapter
description: Review chapter
disable-model-invocation: true
---

# Review: Chapter "$ARGUMENTS"

Take a look at the chapter
- Read the chapter sections (*.md files for that chapter)
- Read the corresponding "hands on" examples in (example_*.ipynb files for that chapter)
- Read the corrsponding "core" library code for that chapter (`agentic_patterns/core/*` files used by that chapter)
- The documentation (docs/* files) related to the chapter and core libraries used by the chapter

The order in each chapter should be:
- Introduction
- Historical Perspectives (if present): All historical perspectives from the chapter should be in a single "Historical Perspectives" section at the start of the chapter
- Main sections 
- Hands-on intro (if present)
- Hands-on sections (if present)
- References: All references from the chapter should be in a single "References" section at the end of the chapter

Look for:
- Accuracy: Is the content accurate and correct?
- Clarity: Is the content clear and easy to understand?
- Inconsistencies: 
  - Are there any inconsistencies between different sections of the chapter, 
  - or between the chapter and the code examples or core libraries?
- Inconsistent styles or formatting
- Missing explanations: Are there any concepts or terms that are used but not explained?
- Duplicated information: Is there any information that is repeated unnecessarily?
- Outdated information: Is there any information that is outdated or no longer relevant?

Output a short assessment of the chapter, listing any issues found and suggestions for improvement.
Don't be nitpicky, focus on the most important issues that would improve the chapter significantly (if there are no issues, just say "No issues found").

READ FILES MANUALLY, DO NOT IMPLEMENT ANY CODE OR RUN ANY COMMANDS.

