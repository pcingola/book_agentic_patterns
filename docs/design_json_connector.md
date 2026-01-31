# JSON File Connector Design

## Overview

Design for a JSON file connector that provides JSON-specific primitives for agents to interact with JSON files in the workspace sandbox. This connector builds on top of the existing generic file connector and integrates with the context processor infrastructure for automatic truncation of large results.

## Requirements

1. **Agent-facing**: Operations designed for direct agent use, not programmer APIs
2. **Workspace sandboxing**: All file operations constrained to `/workspace/...` paths
3. **Context management**: Use JSON processor for read operations to handle truncation of large/deeply nested structures
4. **JSONPath addressing**: Support JSONPath-like syntax for targeted reads and writes
5. **Safe operations**: Validate inputs, prevent accidental overwrites of large unrelated sections
6. **Permission-aware**: Use existing `@tool_permission` decorator

## Critical Design Constraint

**Localized edits only.** Write operations must validate that the edit is targeted and does not accidentally rewrite large unrelated sections. This prevents the agent from inadvertently destroying data through overly broad updates.

**Structure truncation on reads.** JSON files can have deeply nested structures (e.g., 10+ levels), large arrays (10,000+ items), or very long string values. All read operations must route through `process_json()` to ensure proper structure truncation.

## Operations

### Read Operations (ToolPermission.READ)

#### 1. `preview_json(path, max_depth=3, ctx=None) -> str`
Preview JSON file with automatic structure truncation.

**Input:**
- `path`: Sandbox path (e.g., `/workspace/config/app.json`)
- `max_depth`: Maximum nesting depth to display (default 3, max 10)
- `ctx`: Request context for user/session isolation

**Output:**
- Formatted JSON string with truncation summary
- Uses JSON processor for intelligent structure truncation
- Returns `[Error] ...` on failure

**Implementation:**
- Translate sandbox path to host path
- Use `process_json()` with custom config for max_depth
- Format result with truncation info

**Example:**
```python
preview_json("/workspace/config/app.json", max_depth=3)
# Returns: Pretty-printed JSON with arrays/objects truncated at depth 3
#   [Truncation info: 2 arrays truncated, 3 objects truncated, 5 deep structures]
```

#### 2. `get_json_value(path, json_path, ctx=None) -> str`
Get a value or subtree using JSONPath syntax.

**Input:**
- `path`: Sandbox path
- `json_path`: JSONPath expression (e.g., `$.features.rollout`, `$.users[0].name`)
- `ctx`: Request context

**Output:**
- Formatted value (primitives, arrays, or objects)
- Uses JSON processor for subtree truncation if result is large
- Returns `[Error] ...` on failure

**Implementation:**
- Parse JSON file
- Evaluate JSONPath expression
- If result is primitive (string, number, boolean, null), return directly
- If result is array/object, use `process_json()` on the subtree for truncation
- Handle missing paths gracefully

**Example:**
```python
get_json_value("/workspace/config/app.json", "$.features.rollout")
# Returns: {"enabled": true, "percent": 50, "regions": ["us-east-1", "eu-west-1"]}

get_json_value("/workspace/config/app.json", "$.features.rollout.percent")
# Returns: 50
```

#### 3. `list_json_keys(path, json_path="$", ctx=None) -> str`
List keys at a specific path in the JSON structure.

**Input:**
- `path`: Sandbox path
- `json_path`: JSONPath to the object (default root)
- `ctx`: Request context

**Output:**
- Formatted list of keys with type hints
- Example: `"Keys at $.features: rollout (object), darkMode (boolean), analytics (object)"`
- Returns `[Error] ...` on failure

**Implementation:**
- Parse JSON file
- Navigate to json_path
- If target is object, return keys with type info
- If target is array, return `"[Array with N items]"`
- If target is primitive, return type info

**Example:**
```python
list_json_keys("/workspace/config/app.json", "$.features")
# Returns: "Keys at $.features: rollout (object), darkMode (boolean), analytics (object)"

list_json_keys("/workspace/config/app.json", "$.users")
# Returns: "[Array with 42 items]"
```

#### 4. `validate_json(path, ctx=None) -> str`
Validate JSON syntax and structure.

**Input:**
- `path`: Sandbox path
- `ctx`: Request context

**Output:**
- Success: `"Valid JSON: N keys at root, size: 1.2 KB"`
- Failure: `"[Error] Invalid JSON at line 42: unexpected token ','"`

**Implementation:**
- Attempt to parse JSON
- If valid, return summary stats (root type, key count, size)
- If invalid, return parse error with line/column info

**Example:**
```python
validate_json("/workspace/config/app.json")
# Returns: "Valid JSON: 5 keys at root (features, version, env, logging, cache), size: 2.3 KB"
```

### Write Operations (ToolPermission.WRITE)

#### 5. `set_json_value(path, json_path, value, ctx=None) -> str`
Set a value at a specific JSONPath, preserving the rest of the file.

**Input:**
- `path`: Sandbox path
- `json_path`: JSONPath expression (must be specific, not a wildcard)
- `value`: New value (string representation that will be parsed as JSON)
- `ctx`: Request context

**Output:**
- Success: `"Updated $.features.rollout.percent = 25 in /workspace/config/app.json"`
- Returns `[Error] ...` on failure

**Implementation:**
- Parse JSON file
- Validate json_path points to a single location (no wildcards, no multiple matches)
- Parse value string as JSON (supports primitives, arrays, objects)
- Set value at target path
- Preserve formatting if possible (use indent=2 for output)
- Write back to file
- Validate that edit only touched the target path

**Safety checks:**
- Reject wildcard paths (e.g., `$.users[*].status`)
- Reject paths that match multiple locations
- Reject root replacement (must specify a key, not `$`)
- Warn if value is larger than 10KB (prevents accidental large overwrites)

**Example:**
```python
set_json_value("/workspace/config/app.json", "$.features.rollout.percent", "25")
# Returns: "Updated $.features.rollout.percent = 25 in /workspace/config/app.json"

set_json_value("/workspace/config/app.json", "$.features.newFeature", '{"enabled": true}')
# Returns: "Updated $.features.newFeature = {...} in /workspace/config/app.json"
```

#### 6. `delete_json_key(path, json_path, ctx=None) -> str`
Delete a key at a specific JSONPath.

**Input:**
- `path`: Sandbox path
- `json_path`: JSONPath expression (must point to a single key)
- `ctx`: Request context

**Output:**
- Success: `"Deleted $.features.oldFeature from /workspace/config/app.json"`
- Returns `[Error] ...` on failure

**Implementation:**
- Parse JSON file
- Validate json_path points to a single location
- Delete key at target path
- Write back to file
- Validate parent still exists after deletion

**Safety checks:**
- Reject root deletion
- Reject wildcard paths
- Reject paths that don't exist

**Example:**
```python
delete_json_key("/workspace/config/app.json", "$.features.deprecatedFeature")
# Returns: "Deleted $.features.deprecatedFeature from /workspace/config/app.json"
```

#### 7. `append_json_array(path, json_path, value, ctx=None) -> str`
Append a value to an array at a specific JSONPath.

**Input:**
- `path`: Sandbox path
- `json_path`: JSONPath to array
- `value`: Value to append (string representation)
- `ctx`: Request context

**Output:**
- Success: `"Appended value to $.users in /workspace/config/app.json (now 43 items)"`
- Returns `[Error] ...` on failure

**Implementation:**
- Parse JSON file
- Navigate to json_path
- Validate target is an array
- Parse value and append
- Write back to file
- Return new array length

**Example:**
```python
append_json_array("/workspace/config/app.json", "$.users", '{"id": "u-101", "name": "Alice"}')
# Returns: "Appended value to $.users in /workspace/config/app.json (now 43 items)"
```

#### 8. `merge_json_object(path, json_path, updates, ctx=None) -> str`
Merge updates into an object at a specific JSONPath without replacing it entirely.

**Input:**
- `path`: Sandbox path
- `json_path`: JSONPath to object
- `updates`: JSON string with keys to merge (e.g., `'{"key1": "val1", "key2": 123}'`)
- `ctx`: Request context

**Output:**
- Success: `"Merged 2 keys into $.features.rollout in /workspace/config/app.json"`
- Returns `[Error] ...` on failure

**Implementation:**
- Parse JSON file
- Navigate to json_path
- Validate target is an object
- Parse updates string
- Merge updates into target (shallow merge, existing keys overwritten)
- Write back to file
- Return count of merged keys

**Example:**
```python
merge_json_object("/workspace/config/app.json", "$.features.rollout", '{"percent": 75, "regions": ["us-east-1"]}')
# Returns: "Merged 2 keys into $.features.rollout in /workspace/config/app.json"
```

## Technical Details

### File Structure

```
agentic_patterns/core/connectors/
├── __init__.py          # Export all connector functions
├── file.py              # Existing generic file connector
├── csv.py               # Existing CSV connector
└── json.py              # New JSON connector (this design)
```

### Dependencies

- `agentic_patterns.core.workspace`: Path translation, sandboxing
- `agentic_patterns.core.context.processors.json_processor`: JSON reading with truncation
- `agentic_patterns.core.tools.permissions`: `@tool_permission` decorator
- `jsonpath-ng` or similar: JSONPath parsing and evaluation
- `json` module: Reading/writing JSON data
- `pathlib`: Path handling

### JSONPath Support

Use a subset of JSONPath for safety:

**Supported:**
- Root: `$`
- Dot notation: `$.key`, `$.parent.child`
- Bracket notation: `$['key']`, `$['parent']['child']`
- Array index: `$.users[0]`, `$.data[5]`
- Negative index: `$.users[-1]` (last item)

**Not supported (for write operations):**
- Wildcards: `$.users[*]`, `$..name`
- Slices: `$.users[0:5]`
- Filters: `$.users[?(@.age > 18)]`
- Recursive descent: `$..name`

Read operations can support these for inspection, but write operations must reject them to prevent unintended modifications.

### Key Patterns

1. **Path Translation**: Always use `_translate_path(path, ctx)` to convert sandbox paths to host paths
2. **Error Handling**: Return formatted error strings `"[Error] ..."` instead of raising exceptions
3. **Truncation on Reads**: Use `process_json()` for any read operation that returns JSON structures
4. **Localized Writes**: Validate that write operations target a single specific location
5. **Value Parsing**: Parse value strings as JSON to support primitives, arrays, and objects
6. **Formatting Preservation**: Use consistent indentation (indent=2) for readability

### Example Agent Interactions

```python
# Agent previews a JSON config file
preview_json("/workspace/config/app.json", max_depth=2)
# Returns: Pretty-printed JSON, depth limited to 2 levels

# Agent inspects a specific subtree
get_json_value("/workspace/config/app.json", "$.features.rollout")
# Returns: {"enabled": true, "percent": 50, "regions": [...]}

# Agent checks what keys exist
list_json_keys("/workspace/config/app.json", "$.features")
# Returns: "Keys at $.features: rollout (object), darkMode (boolean), analytics (object)"

# Agent validates JSON syntax
validate_json("/workspace/config/settings.json")
# Returns: "Valid JSON: 8 keys at root, size: 4.5 KB"

# Agent updates a specific value
set_json_value("/workspace/config/app.json", "$.features.rollout.percent", "75")
# Returns: "Updated $.features.rollout.percent = 75 in /workspace/config/app.json"

# Agent adds a new feature flag
set_json_value("/workspace/config/app.json", "$.features.newFeature", '{"enabled": true, "beta": true}')
# Returns: "Updated $.features.newFeature = {...} in /workspace/config/app.json"

# Agent removes an old feature
delete_json_key("/workspace/config/app.json", "$.features.deprecatedFeature")
# Returns: "Deleted $.features.deprecatedFeature from /workspace/config/app.json"

# Agent adds a user to an array
append_json_array("/workspace/config/users.json", "$.active", '{"id": "u-101", "name": "Alice"}')
# Returns: "Appended value to $.active in /workspace/config/users.json (now 42 items)"

# Agent updates multiple fields in an object
merge_json_object("/workspace/config/app.json", "$.features.rollout", '{"percent": 100, "complete": true}')
# Returns: "Merged 2 keys into $.features.rollout in /workspace/config/app.json"
```

## Performance Considerations

1. **Deep Nesting**: JSON processor automatically truncates beyond max_nesting_depth (default 10)
2. **Large Arrays**: Processor truncates to max_array_items (default 100)
3. **Large Objects**: Processor truncates to max_object_keys (default 50)
4. **Long Strings**: Individual strings truncated to max_string_value_length (default 1000 chars)
5. **File Size**: Read operations use processor to limit output; safe for multi-MB JSON files
6. **Write Operations**: Parse entire file into memory, modify, write back (standard JSON limitation)

## Safety Features

1. **No Wildcard Writes**: Write operations reject wildcards to prevent unintended bulk modifications
2. **No Root Replacement**: Cannot replace entire document with `set_json_value($, ...)`
3. **Size Warnings**: Warn if attempting to write values >10KB
4. **Type Validation**: Validate target types (e.g., can't append to non-array)
5. **Path Validation**: Ensure json_path points to single location for writes
6. **Workspace Isolation**: All operations constrained to sandbox paths

## Future Enhancements

Not in scope for initial implementation:

- JSON Schema validation
- Bulk updates with wildcards (complex safety implications)
- JSON-to-CSV conversion
- Deep merge (currently shallow merge only)
- JSONPath filters for read operations
- Diff/patch operations
- JSON comments preservation (requires custom parser)

## Testing Strategy

Test coverage should include:

1. **Unit tests** for each operation
2. **JSONPath parsing** (various syntax forms)
3. **Deep structures** (10+ levels) - verify depth truncation works
4. **Large arrays** (1000+ items) - verify array truncation works
5. **Large objects** (100+ keys) - verify object truncation works
6. **Error cases** (missing files, invalid JSON, malformed JSONPath)
7. **Safety checks** (wildcard rejection, root protection, size limits)
8. **Workspace sandboxing** (path traversal attempts)
9. **Edge cases** (empty objects/arrays, null values, special characters in keys)
10. **Type mismatches** (appending to non-array, merging into non-object)

## References

From book chapter "Connectors" (chapters/connectors/connectors.md):

> For JSON, the agent typically needs to inspect a subtree and update a field. JSONPath-like addressing (or a constrained pointer syntax) is enough; the tool should validate that the edit is local and does not accidentally rewrite large unrelated sections:
>
> ```python
> sub = json.get("config/app.json", path="$.features.rollout")
> json.set("config/app.json", path="$.features.rollout.percent", value=25)
> ```
>
> The important pattern is that format-aware methods do not replace the generic file connector; they sit alongside it as "sharp tools" for the top few formats.
