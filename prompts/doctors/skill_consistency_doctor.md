## Script-Documentation Consistency Analyzer

You are checking the consistency between scripts documented in a SKILL.md file and the actual scripts present in the skill directory.

Given:
1. The SKILL.md content (frontmatter + body)
2. A list of script filenames that actually exist in the scripts/ directory

Your task is to identify:

1. **Undocumented scripts**: Scripts that exist in the scripts/ directory but are NOT mentioned or described in SKILL.md. These are problematic because an agent might not know when to use them.

2. **Phantom references**: Script references in SKILL.md that do NOT correspond to any actual script file. These are problematic because an agent might try to run a non-existent script.

3. **Overall documentation coverage**: Are all scripts adequately documented?

Rules:
- Look for explicit script references like `scripts/filename.py` or implicit references like "run the extraction script"
- A script should be considered "mentioned" if its name or purpose is described in the body
- If scripts_present is empty but SKILL.md mentions scripts, flag this as an issue
- If scripts_present has files but SKILL.md never mentions scripts, flag this as an issue
- Set needs_improvement=true if there are any mismatches

SKILL.md content:
{skill_md_content}

Scripts present in scripts/ directory:
{scripts_present}
