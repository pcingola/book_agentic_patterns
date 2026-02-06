# Plan: Private Data Guardrails for Tool Permissions

## Context

The codebase has two independent systems: tool permissions (`ToolPermission` with READ/WRITE/CONNECT and enforcement functions) and private data tracking (`PrivateData` persisted per session). When a session contains private data, CONNECT tools (external APIs, MCP servers) should be blocked to prevent data leakage. Currently nothing connects these two systems.

The key challenge: private data can arrive mid-conversation, so the permission check must happen at tool execution time (dynamic), not at agent construction time (static).

## Code Changes

### 1. Make `enforce_tool_permission` accept a callable -- `permissions.py`

**File**: `agentic_patterns/core/tools/permissions.py`

Change `enforce_tool_permission(func, granted)` so `granted` can be either `set[ToolPermission]` (current behavior, backward compatible) or `Callable[[], set[ToolPermission]]` (dynamic resolution). The wrapper calls the callable on every invocation to get fresh permissions. Same change for `enforce_tools_permissions`.

Type for the parameter: `set[ToolPermission] | Callable[[], set[ToolPermission]]`.

### 2. Add policy function -- `private_data.py`

**File**: `agentic_patterns/core/compliance/private_data.py`

Add `resolve_permissions(base: set[ToolPermission]) -> set[ToolPermission]` that reads the current session's private data state (via `session_has_private_data()` which uses contextvars for user_id/session_id) and removes `CONNECT` from the base set if private data is present. Returns the base set unchanged otherwise.

### 3. Add `sensitivity` field to data source configs

**File**: `agentic_patterns/core/connectors/sql/db_connection_config.py`

Add optional `sensitivity: DataSensitivity = DataSensitivity.PUBLIC` field to `DbConnectionConfig`. Parse it from `dbs.yaml` in `load_from_yaml`.

**File**: `agentic_patterns/core/connectors/openapi/api_connection_config.py`

Add optional `sensitivity: DataSensitivity = DataSensitivity.PUBLIC` field to `ApiConnectionConfig`. Parse it from `apis.yaml` in `load_from_yaml`.

### 4. Auto-mark session when reading from sensitive sources

**File**: `agentic_patterns/core/connectors/sql/connector.py`

In the SQL connector's query execution path, after executing a query, check the source database's `sensitivity`. If not PUBLIC, call `mark_session_private()` and `add_private_dataset(db_id, sensitivity)`.

**File**: `agentic_patterns/core/connectors/openapi/connector.py`

Same pattern in `call_endpoint`: check the API's `sensitivity` from config, mark session if not PUBLIC.

### 5. Tests

**File**: `tests/unit/test_tools_permissions.py`

Add tests for dynamic permission resolution: pass a callable to `enforce_tool_permission`, verify it's called on each invocation, verify permission changes mid-conversation are respected.

**File**: `tests/unit/test_compliance_private_data.py`

Add test for `resolve_permissions`: verify CONNECT is removed when session has private data, verify it's kept when no private data.

**File**: `tests/unit/test_connector_sensitivity.py`

Test that `DbConnectionConfig` and `ApiConnectionConfig` parse `sensitivity` from YAML, default to PUBLIC.

## Chapter / Documentation Changes

### 6. Update Tools chapter -- hands-on for dynamic permissions

**File**: `chapters/tools/hands_on_tool_permissions.md`

Add a new section after "Runtime Enforcement" covering dynamic permission resolution. Explain the callable approach: why static sets are insufficient when session state changes mid-conversation, how passing a callable to `enforce_tools_permissions` makes the check happen on every tool invocation, and a code snippet showing `resolve_permissions` wired as the callable.

### 7. Update Tools chapter -- notebook

**File**: `agentic_patterns/examples/tools/example_tool_permissions.ipynb`

Add cells demonstrating: (a) creating an enforced tool set with a callable that checks private data, (b) calling a CONNECT tool before marking private data (succeeds), (c) marking the session as private mid-conversation, (d) calling the same CONNECT tool again (blocked with `ToolPermissionError`).

### 8. Add hands-on for Private Data in Data Sources chapter

**File**: `chapters/data_sources_and_connectors/hands_on_private_data.md` (new)

Hands-on walkthrough covering: (a) marking a session as private manually, (b) adding datasets with different sensitivity levels and observing the ratchet, (c) configuring `sensitivity` in `dbs.yaml`, (d) querying a sensitive database and observing automatic session tagging, (e) demonstrating that CONNECT tools are blocked after sensitive data enters the workspace.

**File**: `chapters/data_sources_and_connectors/chapter.md`

Add the new hands-on to the chapter index, after the `private_data.md` theory section.

## Verification

Run `scripts/test.sh` to execute all unit tests. Existing tests must still pass (backward compatibility of static `set` argument). New tests verify the dynamic callable path, the policy function, and sensitivity parsing.
