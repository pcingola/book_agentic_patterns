# Hands-On: Human in the Loop

Human-in-the-loop (HITL) is a control pattern where an agent deliberately pauses autonomous execution to request human approval before proceeding with high-impact actions. This hands-on explores the pattern using `example_human_in_the_loop.ipynb`, demonstrating how to build structured checkpoints that give humans authority over irreversible operations.

## The Core Idea

Unlike conversational clarification where the agent asks for more information, HITL treats the human as an authority who can approve, reject, or modify proposed actions. The agent externalizes its intent in a structured format, waits for a decision, and then proceeds accordingly. This creates an auditable control point between planning and execution.

## Scenario: Database Operations

The example implements a database management assistant that can perform three types of operations: read, update, and delete. Read operations execute immediately since they have no side effects. Update and delete operations require explicit human approval because they modify data.

## Modeling Actions with Structured Types

The first step is defining what an "action" looks like. Rather than passing free-form text between components, we use structured types that make the system predictable and inspectable.

```python
class ActionType(str, Enum):
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class ProposedAction:
    action_type: ActionType
    table: str
    description: str
    sql: str

    def requires_approval(self) -> bool:
        return self.action_type in (ActionType.UPDATE, ActionType.DELETE)
```

The `ActionType` enum inherits from both `str` and `Enum`, which allows it to serialize cleanly to JSON or plain text while maintaining type safety. The `ProposedAction` dataclass bundles all information needed to understand and execute an operation. The `requires_approval()` method encodes the policy: reads are safe, modifications are not.

This separation of policy from mechanism is important. The approval logic lives in one place and can be changed without touching the rest of the system. You could extend this to more granular policies, such as requiring approval only for deletes affecting more than N rows, or allowing certain users to bypass approval for specific tables.

## The Planning Agent

The agent receives natural language requests and converts them into structured actions. The system prompt constrains its output format:

```python
PLANNER_PROMPT = """You are a database operations planner. Given a user request, output the SQL operation needed.

Available tables: users (columns: id, name, email, status)

Output format (exactly):
ACTION_TYPE: read|update|delete
TABLE: table_name
DESCRIPTION: brief description of what will happen
SQL: the SQL statement

Be conservative - if a request is ambiguous about what to modify, ask for clarification instead of guessing."""

planner = get_agent(system_prompt=PLANNER_PROMPT)
```

The structured output format serves two purposes. First, it makes parsing reliable since each field appears on its own line with a known prefix. Second, it forces the model to be explicit about what it intends to do, making the action inspectable before execution.

The instruction to "be conservative" is significant. In HITL systems, false positives (asking for approval when not strictly needed) are usually preferable to false negatives (executing a destructive action without approval). The agent should err on the side of caution.

## Parsing the Response

The `parse_action` function converts the agent's text response into a typed `ProposedAction`:

```python
def parse_action(response: str) -> ProposedAction | None:
    lines = response.strip().split("\n")
    data = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip().lower()] = value.strip()

    if not all(k in data for k in ["action_type", "table", "description", "sql"]):
        return None

    try:
        action_type = ActionType(data["action_type"].lower())
    except ValueError:
        return None

    return ProposedAction(
        action_type=action_type,
        table=data["table"],
        description=data["description"],
        sql=data["sql"]
    )
```

The function returns `None` if parsing fails, which the orchestrator handles as an error condition. This defensive approach prevents malformed agent output from causing unexpected behavior downstream.

## The Approval Checkpoint

The `request_human_approval` function is where execution actually pauses for human input:

```python
@dataclass
class ApprovalResult:
    approved: bool
    feedback: str | None = None


def request_human_approval(action: ProposedAction) -> ApprovalResult:
    print("\n" + "="*60)
    print("APPROVAL REQUIRED")
    print("="*60)
    print(f"\nThe agent wants to perform the following action:\n")
    print(action)
    print("\n" + "-"*60)

    while True:
        response = input("Approve? (yes/no/modify): ").strip().lower()
        if response in ("yes", "y"):
            return ApprovalResult(approved=True)
        elif response in ("no", "n"):
            feedback = input("Reason for rejection (optional): ").strip()
            return ApprovalResult(approved=False, feedback=feedback or "Rejected by user")
        elif response == "modify":
            feedback = input("What changes are needed? ")
            return ApprovalResult(approved=False, feedback=f"Modification requested: {feedback}")
        print("Please enter 'yes', 'no', or 'modify'")
```

Several design choices are worth noting. The function presents all relevant information (action type, description, SQL) before asking for a decision, minimizing the cognitive load on the human reviewer. The `ApprovalResult` dataclass captures not just the binary decision but also optional feedback, which can be logged for audit purposes or fed back to the agent. The three response options (yes, no, modify) cover the common cases: proceed as planned, abort entirely, or request changes.

In a production system, this function would likely be replaced by an asynchronous mechanism: a web interface, a Slack message, an email with approval links, or integration with an existing workflow system. The synchronous `input()` call in the notebook demonstrates the concept without introducing infrastructure complexity.

## The Orchestrator

The `process_request` function ties everything together:

```python
async def process_request(user_request: str) -> str:
    print(f"\nUser request: {user_request}")
    print("-" * 40)

    # Step 1: Plan the action
    plan_run, _ = await run_agent(planner, user_request)
    response = plan_run.result.output
    action = parse_action(response)

    if action is None:
        return f"Could not parse action from planner response:\n{response}"

    print(f"\nPlanned action: {action.action_type.value}")

    # Step 2: Check if approval is needed
    if action.requires_approval():
        approval = request_human_approval(action)

        if not approval.approved:
            return f"Action aborted. {approval.feedback}"

        print("\nApproval granted. Executing...")
    else:
        print("\nNo approval needed for read operations. Executing...")

    # Step 3: Execute the action
    result = execute_action(action)
    return result
```

The flow is linear: plan, then conditionally approve, then execute. Each step has clear boundaries. If parsing fails, execution stops with an error message. If approval is required but denied, execution stops with the human's feedback. Only after all checks pass does the action execute.

This structure makes the system predictable. A human reviewer can trace exactly what happened at each step, which is essential for debugging and audit trails.

## Running the Examples

The notebook includes three examples that demonstrate different paths through the system.

**Example 1: Read Operation**

```python
result = await process_request("Show me all users in the database")
```

The agent plans a SELECT query. Since `ActionType.READ` does not require approval, the orchestrator skips the approval step and executes immediately. Output shows the planned action and result without any pause for human input.

**Example 2: Delete Operation**

```python
result = await process_request("Remove all inactive users from the database")
```

The agent plans a DELETE query. The orchestrator detects that approval is required and presents the proposed action. Execution pauses at the `input()` call. If you type "yes", the action executes. If you type "no", execution aborts with your feedback. If you type "modify", the system captures your requested changes (though this example doesn't implement re-planning based on modifications).

**Example 3: Update Operation**

```python
result = await process_request("Update Charlie's email to charlie@new-domain.com")
```

Similar to the delete case, this triggers the approval flow. The human sees exactly what UPDATE statement will run before deciding whether to allow it.

## Design Considerations

**Granularity of approval**: The example uses a coarse policy (all writes require approval). In practice, you might want finer distinctions: deletes require approval but updates to non-critical fields don't, or approval is required only when affecting more than a threshold number of rows.

**Timeout handling**: The synchronous `input()` blocks indefinitely. Production systems need timeout logic: what happens if the human doesn't respond within an hour? A day? Options include automatic rejection, escalation to another approver, or queueing for later review.

**Audit logging**: Every approval decision should be logged with timestamp, approver identity, the proposed action, and the decision. This creates an audit trail for compliance and debugging.

**Batching**: If an agent proposes 50 similar actions, presenting them one by one is tedious. Consider batching related actions into a single approval request, or providing "approve all similar" options.

**Feedback loops**: When a human rejects or modifies a request, that feedback can be valuable training signal. The system could track rejection patterns to improve the agent's proposals over time.

## Comparison with Other Patterns

Human-in-the-loop complements other patterns rather than replacing them. An agent might use Chain-of-Thought to reason about what action to take, then present that action for HITL approval. Self-reflection could improve the quality of the proposed action before human review. Tool use provides the mechanism for actually executing approved actions.

The key distinction is that HITL is about control and authorization, not reasoning. It doesn't make the agent smarter; it makes the system safer by ensuring humans retain authority over consequential decisions.

## When to Use Human-in-the-Loop

HITL is most valuable when actions have irreversible or high-cost consequences: deploying code, modifying production data, sending external communications, executing financial transactions. It's also essential in regulated environments where accountability must remain with humans.

HITL adds latency and requires human attention, so it should be applied selectively. Requiring approval for every minor action defeats the purpose of automation. The goal is to identify the critical control points where human judgment adds genuine value.

## Key Takeaways

Human-in-the-loop creates structured checkpoints where agents pause for human authorization. The pattern consists of three steps: detect the need for approval, present the proposed action in a clear format, and resume based on the human's decision. Typed data structures make actions inspectable and policies explicit. The approval mechanism is separate from the planning and execution logic, allowing it to be swapped for different interfaces (CLI, web, workflow systems) without changing the core flow. HITL is about control and safety, not intelligence, and should be applied to high-impact actions where human judgment genuinely matters.
