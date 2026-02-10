# Plan: Move domain agents to `agentic_patterns/agents/`

## Context

`core/agents/` currently mixes infrastructure (`get_agent`, `run_agent`, `OrchestratorAgent`) with domain-specific agents (`db_catalog`, `vocabulary`, `nl2sql`). The new `sub_agents/` directory adds more domain agents outside `core/`. This creates an inconsistent layout. The goal is to consolidate all domain-specific agents under `agentic_patterns/agents/` with a consistent pattern, keeping `core/agents/` for infrastructure only.

## Target layout

```
agentic_patterns/
  core/agents/           # Infrastructure only (unchanged files)
    agents.py            get_agent(), run_agent()
    models.py            get_model()
    config.py            provider configs
    utils.py             helpers
    orchestrator.py      OrchestratorAgent, AgentSpec

  agents/                # All domain-specific agents (new location)
    db_catalog.py        moved from core/agents/db_catalog.py
    vocabulary.py        moved from core/agents/vocabulary.py
    nl2sql/              moved from core/agents/nl2sql/
      __init__.py
      agent.py
      prompts.py
    data_analysis.py     moved from sub_agents/data_analysis.py
    sql.py               moved from sub_agents/nl2sql.py (renamed for consistency)
    coordinator.py       rewritten to use OrchestratorAgent pattern
```

## Steps

### 1. Create `agentic_patterns/agents/` directory

### 2. Move `core/agents/db_catalog.py` -> `agents/db_catalog.py`

Update import: `from agentic_patterns.core.agents.agents` -> `from agentic_patterns.core.agents`. No external importers found -- no other files to update.

### 3. Move `core/agents/vocabulary.py` -> `agents/vocabulary.py`

Update import path. Fix importers:
- `agentic_patterns/examples/connectors/example_vocabulary.ipynb`
- `chapters/data_sources_and_connectors/hands_on_vocabulary.md`

### 4. Move `core/agents/nl2sql/` -> `agents/nl2sql/`

Move `agent.py` and `prompts.py`. Update `__init__.py` (relative imports stay as-is). Fix importers:
- `agentic_patterns/examples/connectors/example_nl2sql.ipynb`
- `chapters/data_sources_and_connectors/hands_on_nl2sql.md`

### 5. Keep `sub_agents/data_analysis.py` -> `agents/data_analysis.py`

Already correct in form. Just move and update module path.

### 6. Rename `sub_agents/nl2sql.py` -> `agents/sql.py`

The sub_agents version uses `tools/sql.py` (general SQL tools, not db-bound). Rename to `sql.py` to avoid collision with the `agents/nl2sql/` subpackage and to match what it actually does (general SQL agent, not NL2SQL-to-single-db).

### 7. Rewrite `coordinator.py` to use `OrchestratorAgent`

The coordinator should create an `AgentSpec` with the delegation tools and use `OrchestratorAgent`, following the established pattern from `core/agents/orchestrator.py`. The delegation tools (`ask_data_analyst`, `ask_sql_analyst`) will be defined in `coordinator.py` and referenced in the spec's `tools` list.

### 8. Delete `agentic_patterns/sub_agents/` directory

### 9. Update `core/agents/__init__.py`

Remove any stale references. It currently only exports infrastructure (`get_agent`, `run_agent`, `get_model`, `AgentSpec`, `OrchestratorAgent`) so no change needed.

### 10. Update CLAUDE.md

Update the "Repository Structure" and "Core Library" sections to reflect the new `agents/` directory.

## Files modified

| Action | File |
|--------|------|
| Create | `agentic_patterns/agents/db_catalog.py` |
| Create | `agentic_patterns/agents/vocabulary.py` |
| Create | `agentic_patterns/agents/nl2sql/__init__.py` |
| Create | `agentic_patterns/agents/nl2sql/agent.py` |
| Create | `agentic_patterns/agents/nl2sql/prompts.py` |
| Create | `agentic_patterns/agents/data_analysis.py` |
| Create | `agentic_patterns/agents/sql.py` |
| Create | `agentic_patterns/agents/coordinator.py` |
| Delete | `agentic_patterns/core/agents/db_catalog.py` |
| Delete | `agentic_patterns/core/agents/vocabulary.py` |
| Delete | `agentic_patterns/core/agents/nl2sql/` (entire directory) |
| Delete | `agentic_patterns/sub_agents/` (entire directory) |
| Edit   | `agentic_patterns/examples/connectors/example_vocabulary.ipynb` |
| Edit   | `agentic_patterns/examples/connectors/example_nl2sql.ipynb` |
| Edit   | `chapters/data_sources_and_connectors/hands_on_vocabulary.md` |
| Edit   | `chapters/data_sources_and_connectors/hands_on_nl2sql.md` |
| Edit   | `CLAUDE.md` (structure sections) |

## Verification

Run `python -c "from agentic_patterns.agents.db_catalog import select_database"` and similar for each module to confirm imports resolve. Run `scripts/test.sh` if tests exist for these modules.
