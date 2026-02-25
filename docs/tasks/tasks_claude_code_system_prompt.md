# Tasks: Claude Code System Prompt Definitions

Verbatim tool definitions from Claude Code's system prompt relevant to the Tasks system.


## Task Management Tools

### TaskCreate

> Use this tool to create a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.
> It also helps the user understand the progress of the task and overall progress of their requests.
>
> ## When to Use This Tool
>
> Use this tool proactively in these scenarios:
>
> - Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
> - Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
> - Plan mode - When using plan mode, create a task list to track the work
> - User explicitly requests todo list - When the user directly asks you to use the todo list
> - User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
> - After receiving new instructions - Immediately capture user requirements as tasks
> - When you start working on a task - Mark it as in_progress BEFORE beginning work
> - After completing a task - Mark it as completed and add any new follow-up tasks discovered during implementation
>
> ## When NOT to Use This Tool
>
> Skip using this tool when:
> - There is only a single, straightforward task
> - The task is trivial and tracking it provides no organizational benefit
> - The task can be completed in less than 3 trivial steps
> - The task is purely conversational or informational
>
> NOTE that you should not use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.
>
> ## Task Fields
>
> - **subject**: A brief, actionable title in imperative form (e.g., "Fix authentication bug in login flow")
> - **description**: Detailed description of what needs to be done, including context and acceptance criteria
> - **activeForm**: Present continuous form shown in spinner when task is in_progress (e.g., "Fixing authentication bug"). This is displayed to the user while you work on the task.
>
> **IMPORTANT**: Always provide activeForm when creating tasks. The subject should be imperative ("Run tests") while activeForm should be present continuous ("Running tests"). All tasks are created with status `pending`.
>
> ## Tips
>
> - Create tasks with clear, specific subjects that describe the outcome
> - Include enough detail in the description for another agent to understand and complete the task
> - After creating tasks, use TaskUpdate to set up dependencies (blocks/blockedBy) if needed
> - Check TaskList first to avoid creating duplicate tasks

Parameters (from JSON schema):

| Parameter | Required | Type | Description |
|---|---|---|---|
| `subject` | Yes | string | A brief title for the task |
| `description` | Yes | string | A detailed description of what needs to be done |
| `activeForm` | No | string | Present continuous form shown in spinner when in_progress (e.g., "Running tests") |
| `metadata` | No | object | Arbitrary metadata to attach to the task |


### TaskUpdate

> Use this tool to update a task in the task list.
>
> ## When to Use This Tool
>
> **Mark tasks as resolved:**
> - When you have completed the work described in a task
> - When a task is no longer needed or has been superseded
> - IMPORTANT: Always mark your assigned tasks as resolved when you finish them
> - After resolving, call TaskList to find your next task
>
> - ONLY mark a task as completed when you have FULLY accomplished it
> - If you encounter errors, blockers, or cannot finish, keep the task as in_progress
> - When blocked, create a new task describing what needs to be resolved
> - Never mark a task as completed if:
>   - Tests are failing
>   - Implementation is partial
>   - You encountered unresolved errors
>   - You couldn't find necessary files or dependencies
>
> **Delete tasks:**
> - When a task is no longer relevant or was created in error
> - Setting status to `deleted` permanently removes the task
>
> **Update task details:**
> - When requirements change or become clearer
> - When establishing dependencies between tasks
>
> ## Fields You Can Update
>
> - **status**: The task status (see Status Workflow below)
> - **subject**: Change the task title (imperative form, e.g., "Run tests")
> - **description**: Change the task description
> - **activeForm**: Present continuous form shown in spinner when in_progress (e.g., "Running tests")
> - **owner**: Change the task owner (agent name)
> - **metadata**: Merge metadata keys into the task (set a key to null to delete it)
> - **addBlocks**: Mark tasks that cannot start until this one completes
> - **addBlockedBy**: Mark tasks that must complete before this one can start
>
> ## Status Workflow
>
> Status progresses: `pending` -> `in_progress` -> `completed`
>
> Use `deleted` to permanently remove a task.
>
> ## Staleness
>
> Make sure to read a task's latest state using `TaskGet` before updating it.
>
> ## Examples
>
> Mark task as in progress when starting work:
> ```json
> {"taskId": "1", "status": "in_progress"}
> ```
>
> Mark task as completed after finishing work:
> ```json
> {"taskId": "1", "status": "completed"}
> ```
>
> Delete a task:
> ```json
> {"taskId": "1", "status": "deleted"}
> ```
>
> Claim a task by setting owner:
> ```json
> {"taskId": "1", "owner": "my-name"}
> ```
>
> Set up task dependencies:
> ```json
> {"taskId": "2", "addBlockedBy": ["1"]}
> ```

Parameters (from JSON schema):

| Parameter | Required | Type | Description |
|---|---|---|---|
| `taskId` | Yes | string | The ID of the task to update |
| `status` | No | string | New status for the task: `"pending"`, `"in_progress"`, `"completed"`, or `"deleted"` |
| `subject` | No | string | New subject for the task |
| `description` | No | string | New description for the task |
| `activeForm` | No | string | Present continuous form shown in spinner when in_progress (e.g., "Running tests") |
| `owner` | No | string | New owner for the task |
| `metadata` | No | object | Metadata keys to merge into the task. Set a key to null to delete it. |
| `addBlocks` | No | string[] | Task IDs that this task blocks |
| `addBlockedBy` | No | string[] | Task IDs that block this task |


### TaskGet

> Use this tool to retrieve a task by its ID from the task list.
>
> ## When to Use This Tool
>
> - When you need the full description and context before starting work on a task
> - To understand task dependencies (what it blocks, what blocks it)
> - After being assigned a task, to get complete requirements
>
> ## Output
>
> Returns full task details:
> - **subject**: Task title
> - **description**: Detailed requirements and context
> - **status**: 'pending', 'in_progress', or 'completed'
> - **blocks**: Tasks waiting on this one to complete
> - **blockedBy**: Tasks that must complete before this one can start
>
> ## Tips
>
> - After fetching a task, verify its blockedBy list is empty before beginning work.
> - Use TaskList to see all tasks in summary form.

Parameters (from JSON schema):

| Parameter | Required | Type | Description |
|---|---|---|---|
| `taskId` | Yes | string | The ID of the task to retrieve |


### TaskList

> Use this tool to list all tasks in the task list.
>
> ## When to Use This Tool
>
> - To see what tasks are available to work on (status: 'pending', no owner, not blocked)
> - To check overall progress on the project
> - To find tasks that are blocked and need dependencies resolved
> - After completing a task, to check for newly unblocked work or claim the next available task
> - **Prefer working on tasks in ID order** (lowest ID first) when multiple tasks are available, as earlier tasks often set up context for later ones
>
> ## Output
>
> Returns a summary of each task:
> - **id**: Task identifier (use with TaskGet, TaskUpdate)
> - **subject**: Brief description of the task
> - **status**: 'pending', 'in_progress', or 'completed'
> - **owner**: Agent ID if assigned, empty if available
> - **blockedBy**: List of open task IDs that must be resolved first (tasks with blockedBy cannot be claimed until dependencies resolve)
>
> Use TaskGet with a specific task ID to view full details including description and comments.

Parameters: none.


## Spawning Sub-Agents

### Task (sub-agent launcher)

> Launch a new agent to handle complex, multi-step tasks autonomously.
>
> The Task tool launches specialized agents (subprocesses) that autonomously handle complex tasks. Each agent type has specific capabilities and tools available to it.
>
> **Available agent types and the tools they have access to:**
> - **general-purpose**: General-purpose agent for researching complex questions, searching for code, and executing multi-step tasks. (Tools: all)
> - **Explore**: Fast agent specialized for exploring codebases. Use this when you need to quickly find files by patterns, search code for keywords, or answer questions about the codebase. Specify thoroughness: "quick", "medium", or "very thorough". (Tools: all except Task, ExitPlanMode, Edit, Write, NotebookEdit)
> - **Plan**: Software architect agent for designing implementation plans. Returns step-by-step plans, identifies critical files, and considers architectural trade-offs. (Tools: all except Task, ExitPlanMode, Edit, Write, NotebookEdit)
>
> **Parameters:**
> - `description` (required): A short (3-5 word) description of what the agent will do
> - `prompt` (required): The task for the agent to perform
> - `subagent_type` (required): Which agent type to use
> - `model` (optional): "sonnet", "opus", or "haiku". If not specified, inherits from parent.
> - `max_turns` (optional): Maximum number of agentic turns (API round-trips) before stopping.
> - `run_in_background` (optional): Set to true to run this agent in the background. The tool result will include an output_file path.
> - `resume` (optional): Agent ID to resume from previous invocation.
> - `isolation` (optional): "worktree" to run in isolated git worktree.
>
> **Usage notes:**
> - Always include a short description summarizing what the agent will do
> - Launch multiple agents concurrently whenever possible, to maximize performance; use a single message with multiple tool uses
> - When the agent is done, it returns a single message back to you. The result is not visible to the user -- to show results, send a text message with a concise summary.
> - Foreground vs background: Use foreground (default) when you need the agent's results before you can proceed. Use background when you have genuinely independent work to do in parallel.
> - When an agent runs in the background, you will be automatically notified when it completes -- do NOT sleep, poll, or proactively check on its progress. Continue with other work or respond to the user instead.
> - Agents can be resumed using the `resume` parameter by passing the agent ID from a previous invocation.
> - Provide clear, detailed prompts so the agent can work autonomously and return exactly the information you need.
> - Clearly tell the agent whether you expect it to write code or just to do research.

Claude Code-specific agent types (statusline-setup, claude-code-guide) are omitted.

### TaskOutput

> Retrieves output from a running or completed task (background shell, agent, or remote session).
> - Takes a task_id parameter identifying the task
> - Returns the task output along with status information
> - Use block=true (default) to wait for task completion
> - Use block=false for non-blocking check of current status
> - Works with all task types: background shells, async agents, and remote sessions
>
> Parameters:
> - `task_id` (required): The task ID to get output from
> - `block` (default: true): Whether to wait for completion
> - `timeout` (default: 30000, max: 600000): Max wait time in ms

### TaskStop

> Stops a running background task by its ID.
> - Takes a task_id parameter identifying the task to stop
> - Returns a success or failure status
> - Use this tool when you need to terminate a long-running task
>
> Parameters:
> - `task_id`: The ID of the background task to stop
