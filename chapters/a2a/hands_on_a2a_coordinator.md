# Hands-On: A2A Coordinator Agent

This hands-on builds on the basic A2A client-server example to demonstrate a coordinator agent that routes tasks to specialized A2A agents. The coordinator discovers available agents through their Agent Cards, understands their capabilities, and delegates work to the appropriate specialist. This pattern is central to building multi-agent systems where agents with different skills collaborate to solve complex problems.

## Architecture Overview

The system consists of three agents:

1. **Arithmetic Agent** (port 8000) - Performs basic math operations: add, sub, mul, div
2. **Area Calculator Agent** (port 8001) - Calculates areas: triangle, rectangle, circle
3. **Coordinator Agent** (local) - Routes user requests to the appropriate specialist

The coordinator is a regular PydanticAI agent with a tool that can communicate with the A2A agents. It uses the Agent Cards to understand what each specialist can do and includes this information in its system prompt so the LLM can make routing decisions.

## The A2A Servers

Each specialist server follows the same pattern from the basic example, with one addition: they declare their skills explicitly so the Agent Card contains useful capability information.

```python
from agentic_patterns.core.agents import get_agent
from fasta2a import Skill

def tool_to_skill(func: Callable) -> Skill:
    """Convert a tool function to an A2A Skill."""
    return Skill(id=func.__name__, name=func.__name__, description=func.__doc__ or func.__name__)

def add(a: int, b: int) -> int:
    """Add two numbers: a + b"""
    return a + b

# ... more tools ...

tools = [add, sub, mul, div]
skills = [tool_to_skill(f) for f in tools]

agent = get_agent(tools=tools)
app = agent.to_a2a(name="Arithmetic", description="An agent that can perform basic arithmetic operations", skills=skills)
```

The `tool_to_skill()` helper converts tool functions into A2A Skill objects by extracting the function name and docstring. When the agent is exposed via `to_a2a()`, these skills appear in the Agent Card, making them discoverable by clients.

Start both servers before running the notebook:

```bash
# Terminal 1
uvicorn agentic_patterns.a2a.example_a2a_server_1:app --host 0.0.0.0 --port 8000

# Terminal 2
uvicorn agentic_patterns.a2a.example_a2a_server_2:app --host 0.0.0.0 --port 8001
```

## Discovering Agent Capabilities

The coordinator starts by fetching the Agent Card from each known server:

```python
async def agent_card(base_url: str) -> dict:
    """Fetch the agent card from an A2A server."""
    async with httpx.AsyncClient() as http:
        response = await http.get(f"{base_url}/.well-known/agent-card.json")
        return response.json()
```

The Agent Card contains the agent's name, description, and list of skills. A card for the Arithmetic agent looks like:

```json
{
    "name": "Arithmetic",
    "description": "An agent that can perform basic arithmetic operations",
    "skills": [
        {"id": "add", "name": "add", "description": "Add two numbers: a + b"},
        {"id": "sub", "name": "sub", "description": "Subtract two numbers: a - b"},
        {"id": "mul", "name": "mul", "description": "Multiply two numbers: a * b"},
        {"id": "div", "name": "div", "description": "Divide two numbers: a / b"}
    ]
}
```

This metadata-first approach lets the coordinator understand what each agent can do without sending any actual task content.

## Building the Coordinator's System Prompt

The coordinator converts Agent Cards into a description string that becomes part of its system prompt:

```python
def card_to_description(card: dict) -> str:
    """Convert agent card to a description string."""
    descr = f"{card['name']}: {card['description']}\n"
    for skill in card.get('skills', []):
        descr += f"  - {skill['name']}: {skill['description']}\n"
    return descr

agent_descriptions = [card_to_description(card) for card in cards.values()]
agent_descriptions_str = "\n".join(agent_descriptions)

system_prompt = f"""You route tasks to specialized agents.

Available agents:
{agent_descriptions_str}

NEVER perform calculations yourself. Always delegate to the appropriate agent.
Only invoke one agent at a time.
"""
```

The resulting system prompt tells the LLM exactly which agents are available and what each can do. The explicit instruction to never perform calculations ensures the coordinator always delegates rather than attempting work it should not do.

## The Route Tool

The coordinator's power comes from its `route` tool, which handles the full A2A workflow:

```python
async def route(agent_name: str, task_description: str) -> str | None:
    """Route a task to a specialized agent."""
    print(f"Routing to '{agent_name}': {task_description}")
    client = clients_by_name.get(agent_name)
    if not client:
        return f"Agent '{agent_name}' not found"
    result = await send_task(client, task_description)
    text = get_result_text(result)
    print(f"Result: {text}")
    return text
```

The tool takes an agent name and task description. The LLM decides which agent to call based on the system prompt, and the tool handles the A2A protocol details: sending the message, polling for completion, and extracting the result.

The `send_task()` helper encapsulates the polling loop:

```python
async def send_task(client: A2AClient, prompt: str) -> dict:
    """Send a message to an A2A agent and wait for the result."""
    message = Message(
        kind="message",
        role="user",
        parts=[TextPart(kind="text", text=prompt)],
        message_id=str(uuid.uuid4())
    )
    response = await client.send_message(message=message)
    task_id = response['result']['id']

    while True:
        task_result = await client.get_task(task_id=task_id)
        state = task_result['result']['status']['state']
        if state == "completed":
            return task_result
        elif state == "failed":
            raise Exception(f"Task failed: {task_result}")
        await asyncio.sleep(0.2)
```

## Multi-Turn Conversation

The coordinator maintains conversation history, allowing follow-up questions that reference previous results:

```python
message_history = []

prompt = "What is the sum of 40123456789 and 2123456789?"
agent_run, _ = await run_agent(agent=coordinator, prompt=prompt, message_history=message_history, verbose=True)
message_history = agent_run.result.all_messages()

prompt = "From that result, subtract 246913578"
agent_run, _ = await run_agent(agent=coordinator, prompt=prompt, message_history=message_history, verbose=True)
message_history = agent_run.result.all_messages()

prompt = "Calculate the area of a circle with radius equal to half that number"
agent_run, _ = await run_agent(agent=coordinator, prompt=prompt, message_history=message_history, verbose=True)
```

The conversation flows naturally across specialists. The coordinator remembers the previous result (42246913578), understands that subtracting gives 42000000000, and correctly routes the area calculation to the AreaCalculator agent with radius 21000000000.

## Key Takeaways

Agent Cards enable dynamic capability discovery. The coordinator does not hardcode knowledge of what specialists can do. Instead, it fetches this information at runtime and incorporates it into its prompt. This makes the system extensible: adding a new specialist requires only starting another A2A server.

The coordinator pattern separates concerns cleanly. The coordinator handles user interaction and routing decisions. Specialists handle domain-specific computation. Neither needs to understand the other's internal implementation.

A2A provides the interoperability layer. The specialists could be implemented in different frameworks, run on different machines, or be maintained by different teams. The coordinator only needs to speak the A2A protocol to work with them.

Tools bridge local agents and remote A2A agents. The `route` tool wraps A2A client operations in a function the local LLM can call. This pattern works for any external service: wrap the protocol details in a tool, and the agent can use it like any other capability.
