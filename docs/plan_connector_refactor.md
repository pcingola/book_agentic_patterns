# Plan: Connector Refactoring -- Shared Base Class + Proper Abstractions

## Status

Phase 1 (class-based connectors with static methods) -- DONE previously.
Phase 2 (base class, inheritance, instance methods, SqlConnector) -- DONE.

## What's Done

1. `agentic_patterns/core/connectors/base.py` -- `Connector` ABC created
2. `FileConnector` -- instance methods, inherits `Connector`, `_translate_path` as instance method
3. `CsvConnector` -- inherits `FileConnector`, overrides `head/tail/append`, renames `delete` -> `delete_rows`, `find` -> `find_rows`, extracts `_resolve_column` helper
4. `JsonConnector` -- inherits `FileConnector`, overrides `head/tail/append`, renames `delete` -> `delete_key`, adds `get/set/keys/merge/validate`
5. `VocabularyConnector` -- inherits `Connector`, instance methods, no `@tool_permission`
6. `SqlConnector` -- new class in `sql/connector.py`, inherits `Connector`, self-contained (old `sql/operations.py` removed)
7. All `@tool_permission` decorators removed from connector classes
8. `__init__.py` exports `Connector`, `FileConnector`, `CsvConnector`, `JsonConnector`
9. `vocabulary/agent.py` -- uses `_connector = VocabularyConnector()` instance
10. `sql/nl2sql/tools.py` -- uses `SqlConnector()` instance
11. All tests updated to use instances (223 tests pass)
12. Examples updated: `json_connector_example.py`, `sql_connector_example.py`, `example_file_connector.ipynb`

## Phase 3: Separate Connectors from Agent/Tool Code

Connectors are pure data-access abstractions. Agent creation, tool wrappers, and framework-specific code (PydanticAI) must live outside `connectors/`.

### Moves

| What | From | To |
|---|---|---|
| Vocabulary agent factory | `connectors/vocabulary/agent.py` | `core/agents/vocabulary.py` |
| NL2SQL tool wrappers | `connectors/sql/nl2sql/tools.py` | `core/tools/nl2sql.py` |
| NL2SQL agent + prompts | `connectors/sql/nl2sql/agent.py`, `prompts.py` | `core/agents/nl2sql/` |
| DB catalog agent | `connectors/sql/db_catalog/agent.py` | `core/agents/db_catalog.py` |

### Stays in `connectors/sql/`

Schema inspection (`inspection/`), annotation (`annotation/`), and CLI (`cli/`) stay. They prepare metadata for the connector -- not agent code, even though annotation uses LLMs internally.

### Additional cleanup

- Add a `Strategy` Protocol class in `vocabulary/strategy.py` defining the shared interface (`lookup`, `search`, `validate`, `suggest`, `parent`, `children`, `siblings`, `ancestors`, `descendants`, `roots`, `relationships`, `related`, `subtree`, `info`). Have `StrategyEnum`, `StrategyTree`, and `StrategyRag` implement it. Update `registry.py` type annotations to use `Strategy` instead of bare dicts/Any.
- Remove empty `nl2sql/` and `db_catalog/` directories from `connectors/sql/` after moves.
- Update all imports across examples, tests, and agents.

### Status

TODO.

## Class Hierarchy

```
Connector (ABC)                         # base.py
  FileConnector                         # file.py
    CsvConnector                        # csv.py -- inherits delete/edit/find/list/read/write
    JsonConnector                       # json.py -- inherits delete/edit/find/list/read/write
  VocabularyConnector                   # vocabulary/connector.py
  SqlConnector                          # sql/connector.py
```

## Method Overview

| Concept       | FileConnector | CsvConnector      | JsonConnector     |
|---------------|---------------|-------------------|-------------------|
| Schema        | --            | `headers`         | `keys`            |
| Head          | `head(n=10)`  | `head(n=10)`      | `head(jp, n=10)`  |
| Tail          | `tail(n=10)`  | `tail(n=10)`      | `tail(jp, n=10)`  |
| Point read    | `read`        | `read_row`        | `get`             |
| Text search   | `find`        | `find` (inherited)| `find` (inherited)|
| Column search | --            | `find_rows`       | --                |
| Full write    | `write`       | `write` (inh.)    | `write` (inh.)    |
| Append        | `append`      | `append`          | `append`          |
| Point write   | `edit`        | `update_cell`     | `set`             |
| Row/obj write | --            | `update_row`      | `merge`           |
| Delete file   | `delete`      | `delete` (inh.)   | `delete` (inh.)   |
| Delete data   | --            | `delete_rows`     | `delete_key`      |
| Validate      | --            | --                | `validate`        |
| List          | `list`        | `list` (inh.)     | `list` (inh.)     |
