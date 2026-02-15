
REPL:
- [x] Dirs are wrong: /workspace/.repl and /workspace/mcp_repl/cells.json
- [x] Add a new tool "create jupyter notebook" so that the agent can create a notebook the users can download and open in VS-Code
- [x] If neither bwrap nor docker is available => Exception with clear message. NO silently fall back to a dangerous non-sandboxed execution. Same for sandbox!
- [x] Cell errors should NOT print the full stack trace going through internal REPL code. Instead, it should print a clear error message with the cell content and the error message. The stack trace should be cut when we hit the REPL code. This is to avoid overwhelming the user with internal details and to focus on the relevant error information.

Implement each item, update documentation, then mark it as done before going on to the next item in the list.
