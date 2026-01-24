## Hands-On: Agent Hand-Off

Hand-off is a pattern where one agent transfers control entirely to another. Unlike delegation, where the parent agent retains control and incorporates results, hand-off means the original agent's job is done once it decides who should take over. The receiving agent handles the request completely and independently.

This hands-on explores hand-off through `example_hand_off.ipynb`. A customer support triage agent classifies incoming requests and routes them to specialists. The routing happens in application code, not through tool calls, making the control transfer explicit and visible.

## Hand-Off vs. Delegation

In delegation, the parent agent calls a specialist through a tool, waits for the result, and continues processing. The parent decides what to do with the result and may call additional tools or produce a final response that incorporates the specialist's output.

In hand-off, the first agent's only job is to decide who handles the request. Once that decision is made, the first agent exits. The specialist receives the original request and handles it from start to finish. There is no return path, no incorporation of results, and no further involvement from the routing agent.

This distinction matters architecturally. Delegation creates a hierarchy where the parent owns the conversation. Hand-off creates a routing layer where specialists own their domains independently. Hand-off is appropriate when the routing decision is the only value the first agent provides, and when specialists are capable of handling requests end-to-end.

## The Classification Output

The triage agent produces a structured classification that drives routing:

```python
class RequestCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"


class TriageResult(BaseModel):
    category: RequestCategory = Field(description="The category of the request")
    summary: str = Field(description="Brief summary of the customer's issue")
```

The enum constrains the category to known values. This is important for hand-off because the routing logic must map classifications to specialists. If the agent could return arbitrary strings, the routing code would need fuzzy matching or error handling for unknown categories. With an enum, the mapping is exhaustive and type-safe.

The summary field captures the agent's understanding of the issue. While not strictly necessary for routing, it provides observability into the triage decision and could be logged for quality monitoring.

## The Triage Agent

The triage agent has a narrow responsibility:

```python
triage_agent = get_agent(
    output_type=TriageResult,
    system_prompt="""You are a customer support triage agent.
Classify incoming requests as either billing or technical.
Billing: payments, invoices, subscriptions, refunds, pricing.
Technical: bugs, errors, how-to questions, feature requests, integrations."""
)
```

The system prompt defines the classification criteria explicitly. This specificity reduces ambiguity and makes the agent's behavior more predictable. The agent does not attempt to solve the customer's problem; it only categorizes.

This separation of concerns is intentional. Triage agents should be fast and reliable. Keeping them focused on classification, without the complexity of actually handling requests, makes them easier to test and tune.

## The Specialist Agents

Each specialist handles a specific category:

```python
billing_agent = get_agent(
    system_prompt="""You are a billing support specialist.
Help customers with payments, invoices, subscriptions, and refunds.
Be helpful and provide clear next steps."""
)

technical_agent = get_agent(
    system_prompt="""You are a technical support specialist.
Help customers with bugs, errors, how-to questions, and integrations.
Provide clear explanations and actionable solutions."""
)
```

Specialists have domain-specific prompts that guide their responses. They receive the original customer message directly, not a transformed version from the triage agent. This preserves the full context and avoids information loss during routing.

## The Hand-Off Logic

The routing function makes the hand-off explicit:

```python
async def handle_support_request(customer_message: str) -> str:
    """Route a customer request to the appropriate specialist."""

    # Step 1: Triage classifies the request
    triage_run, _ = await run_agent(triage_agent, customer_message)
    classification = triage_run.result.output

    print(f"Triage: {classification.category.value} - {classification.summary}")

    # Step 2: Hand off to specialist (triage is done)
    match classification.category:
        case RequestCategory.BILLING:
            specialist = billing_agent
        case RequestCategory.TECHNICAL:
            specialist = technical_agent

    # The specialist handles the request completely
    specialist_run, _ = await run_agent(specialist, customer_message)
    return specialist_run.result.output
```

The control flow is sequential but ownership transfers. After the triage agent runs, the function extracts the classification and selects a specialist using a match statement. The triage agent is not involved in any subsequent processing.

The match statement maps categories to agents. Because the category is an enum, the match is exhaustive: every possible value has a corresponding case. This eliminates the need for a default case or error handling for unknown categories.

The specialist receives `customer_message` directly, the same input the triage agent received. This is a design choice. Alternatively, you could pass the triage summary or a transformed prompt. Passing the original message ensures the specialist sees exactly what the customer wrote, which often matters for tone and context.

## Control Flow Comparison

Consider the difference between delegation and hand-off in terms of what each agent sees:

In delegation, the parent agent might process a request like this: receive message, reason about it, call fact-check tool, receive result, incorporate result, continue reasoning, produce final response. The parent sees everything and makes all final decisions.

In hand-off, the flow is: triage receives message, produces classification, exits. Specialist receives message, produces response. The triage agent never sees the specialist's response. The specialist never sees the triage classification (unless explicitly passed).

This separation is both a constraint and a feature. It constrains because you cannot have the triage agent refine or validate the specialist's response. It is a feature because each agent's responsibility is clearly bounded, making the system easier to reason about and modify.

## When to Use Hand-Off

Hand-off is appropriate when the routing decision is valuable on its own and when specialists can handle requests independently. Common scenarios include customer support routing, document classification pipelines, and intent-based dispatchers.

Hand-off is less appropriate when you need the routing agent to validate or refine the specialist's work, when the conversation requires back-and-forth between multiple agents, or when the routing decision depends on information that only emerges during specialist processing.

## Key Takeaways

Hand-off transfers control entirely from one agent to another. The routing agent classifies or decides, then exits. The specialist handles the request end-to-end.

Routing logic lives in application code, not in agent tools. This makes control flow explicit and testable. The match statement maps classifications to agents with type safety.

Structured output with enums ensures routing decisions map to known specialists. This eliminates ambiguity and error handling for unknown categories.

Specialists receive the original input directly. This preserves context and avoids information loss during routing.

Hand-off creates clear ownership boundaries. Each agent is responsible for its domain, and the routing layer simply connects them.
