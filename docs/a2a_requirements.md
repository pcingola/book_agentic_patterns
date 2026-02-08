# A2A Server Requirements

1. **Server Creation**: Create agent via `get_agent()`, expose via `agent.to_a2a(name, description, skills)`; skills MUST reflect actual capabilities -- `tool_to_skill()` for simple agents, explicit declarations when capabilities come from sub-agents, MCP servers, or SKILL.md (`core/agents/`, `fasta2a.Skill`)
2. **Auth**: Bearer token in `Authorization` header; call `set_user_session_from_token(token)` to propagate `sub`/`session_id` into contextvars -- same identity mechanism as MCP (`core/user_session.py`, `core/auth.py`)
3. **Config**: Client configs in `config.yaml` under `a2a.clients` with `${VAR}` env expansion (`core/a2a/config.py`)
4. **Coordination**: `create_coordinator()` fetches agent cards, creates one delegation tool per agent, auto-generates system prompt; delegation tools return `[COMPLETED]`, `[INPUT_REQUIRED:task_id=...]`, `[FAILED]`, `[CANCELLED]`, `[TIMEOUT]` (`core/a2a/coordinator.py`, `core/a2a/tool.py`)
5. **Resilience**: `A2AClientExtended` wraps `fasta2a` client with exponential backoff retry, configurable timeout with auto-cancel, and `is_cancelled` callback for cooperative cancellation (`core/a2a/client.py`)
6. **Prompts**: System prompts and prompt templates MUST be stored in separate markdown files and loaded via `load_prompt()` from `core/prompt.py` -- not hardcoded as inline strings. Each A2A server MUST have its own subdirectory under `prompts/a2a/` to avoid confusion (e.g. `prompts/a2a/nl2sql/system_prompt.md`)
7. **Testing**: Use `MockA2AServer` for unit/integration tests; structure in `tests/unit/` and `tests/integration/` (`core/a2a/mock.py`)
