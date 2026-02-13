## Hands-On: ReAct (Reasoning + Acting)

ReAct is a prompting pattern where the model explicitly interleaves reasoning steps with actions. The model writes structured text containing "Thought" and "Action" labels, the system parses and executes the action, and the resulting observation is appended back to the context. This loop continues until the model produces a final answer.

This hands-on explores ReAct using `example_react.ipynb`, demonstrating how the pattern enables models to interact with external systems while maintaining explicit reasoning traces.

### The Problem: Closed-Book Reasoning

Chain-of-Thought prompting improves reasoning by making intermediate steps explicit, but it operates in a "closed-book" mode. The model must generate all facts from memory, which leads to hallucination when the task requires information the model doesn't have or cannot reliably recall. Consider asking a model about the status of a specific order in your database. No amount of reasoning will help if the model cannot access the actual data.

ReAct solves this by allowing the model to take actions that retrieve information from external systems. Instead of inventing facts, the model can look them up.

### The ReAct Format

The original ReAct paper (Yao et al., 2022) introduced a simple text-based format for interleaving reasoning with actions:

```
Question: [the user's question]
Thought: [model's reasoning about what to do next]
Action: [structured action like Search[topic] or Lookup[id]]
Observation: [result from executing the action]
Thought: [reasoning about the observation]
Action: [next action or Finish[answer]]
```

This format has three key properties. First, the model explicitly states its reasoning before each action, making the decision process transparent. Second, actions use a structured format that the system can parse and execute. Third, observations from the environment are fed back into the context, allowing the model to incorporate real information into its reasoning.

### The Environment

In ReAct, the "environment" is the set of actions available to the model. In the original paper, this was a Wikipedia search API. In our example, we simulate an order tracking system:

```python
ORDERS = {
    "ORD-7842": {"customer": "alice", "status": "shipped", "carrier": "FedEx", ...},
    "ORD-7843": {"customer": "bob", "status": "processing", ...},
    "ORD-7844": {"customer": "alice", "status": "delivered", ...},
}

CUSTOMERS = {
    "alice": {"orders": ["ORD-7842", "ORD-7844"], ...},
    "bob": {"orders": ["ORD-7843"], ...},
}
```

This data is completely arbitrary. The model cannot know order statuses, tracking numbers, or customer associations from its training data. It must use actions to retrieve this information.

The `execute_action` function parses action text and returns observations:

```python
def execute_action(action_text: str) -> str:
    if action_text.startswith("LookupOrder[") and action_text.endswith("]"):
        order_id = action_text[12:-1].strip().upper()
        if order_id in ORDERS:
            o = ORDERS[order_id]
            return f"Order {order_id}: Status={o['status']}, Items={o['items']}"
        return f"Order '{order_id}' not found."
    # ... similar for LookupCustomer and Finish
```

This is the bridge between the model's text output and the external system. The model writes `Action: LookupOrder[ORD-7843]`, and the system returns `Order ORD-7843: Status=processing, Items=['Mechanical Keyboard']`.

### The ReAct Prompt

The prompt teaches the model the expected format through instruction and a few-shot example:

```python
REACT_PROMPT = """You are a customer service assistant. Answer questions by interleaving Thought, Action, and Observation steps.

Available actions:
- LookupCustomer[name]: Get customer info including their order IDs
- LookupOrder[order_id]: Get order details including status and tracking
- Finish[answer]: Return the final answer

Always follow this format:
Thought: reasoning about what to do
Action: one of the available actions

Example:
Question: What is the status of order ORD-1234?
Thought: I need to look up order ORD-1234 to find its status.
Action: LookupOrder[ORD-1234]
Observation: Order ORD-1234: Status=shipped, Items=['Book'], Carrier=USPS, Tracking=9400111899
Thought: The order has been shipped via USPS. I can now answer.
Action: Finish[Order ORD-1234 has been shipped via USPS. Tracking number: 9400111899]

Now answer the following question. Generate ONLY the next Thought and Action (stop after Action, do not generate Observation yourself).
"""
```

The prompt explicitly tells the model not to generate observations itself. This is important because observations must come from the actual system, not from the model's imagination.

### The ReAct Loop

The core of ReAct is a loop that alternates between model generation and action execution:

```python
async def react_loop(question: str, max_steps: int = 5) -> str:
    agent = get_agent(system_prompt=REACT_PROMPT)
    trajectory = f"Question: {question}\n"

    for step in range(max_steps):
        # Get next Thought + Action from the model
        agent_run, _ = await run_agent(agent, trajectory)
        response = agent_run.result.output.strip()
        trajectory += response + "\n"

        # Parse the action
        action_match = re.search(r"Action:\s*(.+?)(?:\n|$)", response)
        action = action_match.group(1).strip()

        # Check for termination
        if action.startswith("Finish["):
            return action[7:-1]

        # Execute action and append observation
        observation = execute_action(action)
        trajectory += f"Observation: {observation}\n"

    return "Max steps reached without final answer."
```

The trajectory accumulates the entire interaction history. Each iteration, we send the full trajectory to the model, which generates the next thought and action based on everything that came before. This allows the model to reason about all previous observations when deciding what to do next.

### Example 1: Single Lookup

A simple question requiring one action:

```
Question: What is the status of order ORD-7843?

--- Step 1 ---
Thought: I need to look up order ORD-7843 to find its status.
Action: LookupOrder[ORD-7843]
Observation: Order ORD-7843: Status=processing, Items=['Mechanical Keyboard']

--- Step 2 ---
Thought: The order is currently being processed. I can now answer.
Action: Finish[Order ORD-7843 is currently processing. It contains a Mechanical Keyboard.]

=== Final Answer: Order ORD-7843 is currently processing. It contains a Mechanical Keyboard. ===
```

The model correctly identifies that it needs to look up the order, retrieves the information, and formulates an answer based on the actual data.

### Example 2: Multi-Step Reasoning

A more complex question requiring multiple lookups:

```
Question: Has Alice received all her orders? If not, which ones are still pending?

--- Step 1 ---
Thought: I need to find Alice's orders first, then check the status of each one.
Action: LookupCustomer[Alice]
Observation: Customer alice: Orders=['ORD-7842', 'ORD-7844'], Email=alice@example.com

--- Step 2 ---
Thought: Alice has two orders. I need to check the status of each to see if they've been delivered.
Action: LookupOrder[ORD-7842]
Observation: Order ORD-7842: Status=shipped, Items=['Wireless Mouse', 'USB Hub'], Carrier=FedEx, Tracking=FX-9981234

--- Step 3 ---
Thought: ORD-7842 is shipped but not delivered. I need to check ORD-7844.
Action: LookupOrder[ORD-7844]
Observation: Order ORD-7844: Status=delivered, Items=['Monitor Stand'], Carrier=UPS, Tracking=1Z999AA10123

--- Step 4 ---
Thought: ORD-7844 has been delivered, but ORD-7842 is still in transit. I can now answer.
Action: Finish[No, Alice has not received all her orders. ORD-7844 (Monitor Stand) was delivered, but ORD-7842 (Wireless Mouse, USB Hub) is still shipped and in transit via FedEx.]

=== Final Answer: No, Alice has not received all her orders. ... ===
```

The model chains multiple lookups together, accumulating information across steps. It first retrieves Alice's order IDs, then checks each order's status, and finally synthesizes a complete answer. Without ReAct, the model would have to guess at order statuses, likely producing a hallucinated response.

### ReAct as a Precursor to Tool Calling

Modern LLM APIs provide built-in tool calling mechanisms where the model outputs structured JSON instead of text like `Action: LookupOrder[ORD-7843]`. These APIs handle parsing, validation, and execution automatically. However, understanding ReAct is valuable because it reveals the underlying pattern that tool calling implements.

The key insight is the separation of concerns: the model proposes actions based on reasoning, the system executes those actions and returns results, and the model incorporates results into its next reasoning step. This loop structure appears in all agentic systems, whether implemented through text parsing or native tool calling APIs.

### When ReAct Helps

ReAct is most valuable when tasks require external information that the model cannot reliably produce from memory. This includes database lookups, API calls, file system operations, and any interaction with systems that have state the model doesn't know. The explicit reasoning traces also provide transparency into the model's decision-making process, making it easier to debug failures and understand why the model took particular actions.

ReAct is less valuable for tasks where all necessary information exists in the prompt or the model's training data. If the model already knows the answer, adding a lookup step just increases latency without improving accuracy.

### Key Takeaways

ReAct interleaves reasoning with actions in a structured text format. The model writes explicit thoughts and actions, the system parses and executes actions, and observations are appended to the context for the next iteration.

The pattern enables models to access external information instead of hallucinating. By forcing the model to retrieve data through actions, we ground its reasoning in actual facts rather than invented ones.

ReAct is a precursor to modern tool calling APIs. Understanding the pattern helps clarify what tool calling does under the hood: propose actions, execute them, observe results, and reason about next steps.

The explicit reasoning traces provide transparency. We can see exactly what the model was thinking at each step, making it easier to debug problems and verify that the model is reasoning correctly.
