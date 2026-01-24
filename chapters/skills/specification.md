## Skills Specification

The Agent Skills specification defines a minimal, filesystem-based format for packaging agent capabilities. A skill is a directory with a required `SKILL.md` file and optional supporting directories. The format is deliberately simple: YAML frontmatter for machine-readable metadata, Markdown body for agent instructions, and conventional directories for scripts and references.

### Directory structure

A skill is a directory containing at minimum a `SKILL.md` file:

```
skill-name/
  SKILL.md
```

The directory name must match the `name` field in the frontmatter. Optional subdirectories extend the skill's capabilities:

```
skill-name/
  SKILL.md
  scripts/
    extract.py
    validate.sh
  references/
    REFERENCE.md
    api-docs.md
  assets/
    template.json
    schema.yaml
```

The `scripts/` directory contains executable code. The `references/` directory contains additional documentation loaded on demand. The `assets/` directory holds static resources like templates and schemas. This separation supports progressive disclosure: the agent loads each tier only when needed.

### SKILL.md format

The `SKILL.md` file combines structured metadata with natural-language instructions. It must begin with YAML frontmatter delimited by `---` markers, followed by Markdown content.

#### Required frontmatter fields

Two fields are mandatory:

```yaml
---
name: pdf-processing
description: Extract text and tables from PDF files, fill forms, merge documents.
---
```

The `name` field identifies the skill. It must be 1-64 lowercase characters, using only letters, numbers, and hyphens. It cannot start or end with a hyphen, cannot contain consecutive hyphens, and must match the parent directory name.

The `description` field explains what the skill does and when to use it. It must be 1-1024 characters. A good description includes specific keywords that help agents identify relevant tasks:

```yaml
description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

A poor description like "Helps with PDFs" provides insufficient signal for skill selection.

#### Optional frontmatter fields

Several optional fields support additional use cases:

```yaml
---
name: pdf-processing
description: Extract text and tables from PDF files, fill forms, merge documents.
license: Apache-2.0
compatibility: Requires PyMuPDF library and network access for cloud storage.
metadata:
  author: example-org
  version: "1.0"
allowed-tools: Bash(python:*) Read
---
```

The `license` field specifies licensing terms, either as a license name or reference to a bundled file.

The `compatibility` field (max 500 characters) indicates environment requirements: intended products, system packages, network access needs. Most skills do not need this field.

The `metadata` field is an arbitrary key-value map for properties not defined by the specification. Implementations can use this for versioning, authorship, or custom attributes.

The `allowed-tools` field is a space-delimited list of pre-approved tools the skill may use. This field is experimental and support varies between agent implementations.

#### Body content

The Markdown body after the frontmatter contains the skill instructions. There are no format restrictions. The content should help agents perform the task effectively.

Recommended sections include step-by-step instructions, examples of inputs and outputs, and common edge cases. The agent loads the entire body when it activates the skill, so keep the main `SKILL.md` under 500 lines and move detailed reference material to separate files.

A typical body structure:

```markdown
# PDF Processing

## When to use this skill

Use this skill when the task involves reading, extracting, or transforming content from PDF documents.

## How to use

For standard extraction, run the bundled script:

python scripts/extract.py <file.pdf>

## Output

Return extracted text with page numbers and any detected tables in a structured format.

## Notes

If you encounter scanned PDFs or complex layouts, consult the reference file.
```

### Progressive disclosure tiers

The specification formalizes the three disclosure tiers introduced earlier:

1. **Metadata** (~100 tokens): The `name` and `description` fields, loaded at startup for all skills.

2. **Instructions** (<5000 tokens recommended): The full `SKILL.md` body, loaded when the skill is activated.

3. **Resources** (as needed): Files in `scripts/`, `references/`, and `assets/`, loaded only when explicitly required by the agent.

### File references

When referencing other files in a skill, use relative paths from the skill root:

```markdown
See [the reference guide](references/REFERENCE.md) for details.

Run the extraction script:
scripts/extract.py
```

Keep file references one level deep from `SKILL.md`. Deeply nested reference chains make skills harder to understand and maintain.

### Scripts directory

The `scripts/` directory contains executable code that agents can run. Scripts should be self-contained or clearly document dependencies, include helpful error messages, and handle edge cases gracefully.

Supported languages depend on the agent implementation. Common options include Python, Bash, and JavaScript. The specification does not prescribe execution details; these are left to the runtime.

### References directory

The `references/` directory contains additional documentation that agents can read when needed. Common patterns include:

- `REFERENCE.md` for detailed technical reference
- Domain-specific files like `security-checklist.md` or `api-docs.md`
- Form templates or structured data formats

Keep individual reference files focused. Agents load these on demand, so smaller files mean more efficient use of context.

### Assets directory

The `assets/` directory contains static resources: document templates, configuration templates, images, diagrams, lookup tables, and schemas. These files are read-only resources that support skill execution without being instructions themselves.

### Validation

The specification includes naming and format constraints that can be validated programmatically. The `name` field must follow strict conventions: lowercase alphanumeric with hyphens, no leading or trailing hyphens, no consecutive hyphens, and matching the directory name. The `description` field must be non-empty and within length limits.

Agent implementations should validate skills at discovery time and reject malformed entries rather than failing at activation.
