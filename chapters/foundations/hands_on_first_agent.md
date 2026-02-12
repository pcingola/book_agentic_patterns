## Hands-On: Building Your First Agent

This section walks through creating and running a simple agent. We use Pydantic-ai as our framework, but the underlying concepts apply universally to all agentic frameworks.

We'll follow the example code in `agentic_patterns/examples/foundations/example_translate_basic.ipynb`.

## High-Level Overview

Building an agent involves three fundamental steps:

**Create an agent** by specifying which language model to use (Claude, GPT-4, Llama, etc.) along with any configuration like timeouts and API credentials.

**Run the agent** with a prompt. The agent sends your prompt to the model, handles any tool calls if needed, and manages the conversation flow until getting a final response.

**Access the results** including the model's output, token usage statistics, and execution details.

While these concepts are universal, each framework provides different APIs and abstractions. We use Pydantic-ai because it provides a clean, Pythonic interface with strong typing and validation through Pydantic models.

## Framework vs. Helper Library

**Pydantic-ai** is the core framework that provides the `Agent` class and handles all agent execution, model interaction, tool calling, and message flow. It's the actual agentic framework doing the work.

**Our helper library** (`agentic_patterns.core.agents`) is a thin wrapper we created to simplify model configuration. Instead of hardcoding API keys and model names in Python code, we use YAML configuration files. This is a best practice that makes it easy to switch models, manage credentials, and configure different environments without changing code.

The key distinction: Pydantic-ai provides the agent functionality. Our library just makes it easier to configure which model to use.

## Configuration: YAML Best Practice

Before running agents, we need to configure which model to use. Rather than hardcoding this in Python, we define it in `config.yaml`:

```yaml
models:
  default:
    model_family: openrouter
    model_name: anthropic/claude-sonnet-4.5
    api_key: your-api-key-here
    api_url: https://openrouter.ai/api/v1
    timeout: 120
```

This configuration approach offers several advantages. You can define multiple model configurations (local models for development, production models with different capabilities) and switch between them without code changes. Credentials stay in configuration files, not scattered through code. Different team members can use different models based on their access and requirements.

Our library supports multiple model families: Azure OpenAI, AWS Bedrock, Ollama for local models, OpenRouter for multi-provider access, and direct OpenAI API.

## Simple Translation Agent

Let's walk through our first example in `agentic_patterns/examples/foundations/example_translate_basic.ipynb`.

### Step 1: Create the Agent

```python
from agentic_patterns.core.agents import get_agent, run_agent

agent = get_agent()
```

The `get_agent()` function is part of our helper library. It reads the configuration from `config.yaml`, initializes the appropriate model (e.g. Claude via OpenRouter), and creates a Pydantic-ai `Agent` object.

What's actually happening: our library reads the YAML file, extracts the model configuration, creates the appropriate Pydantic-ai model instance (like `OpenAIChatModel` or `BedrockConverseModel`), and passes it to Pydantic-ai's `Agent` constructor.

If you wanted to use Pydantic-ai directly without our wrapper, you would write:

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel

model = OpenAIChatModel(model_name='gpt-4', api_key='your-key')
agent = Agent(model=model)
```

Our `get_agent()` simply automates this boilerplate by reading from configuration.

### Step 2: Run the Agent

```python
prompt = "Translate to French: I like coffee."
agent_run, nodes = await run_agent(agent, prompt)
```

The `run_agent()` function is another helper from our library. It wraps Pydantic-ai's agent execution with error handling and logging. Under the hood, it calls the Pydantic-ai agent's iteration interface which streams execution events.

The function returns two objects:

**agent_run**: Pydantic-ai's `AgentRun` object containing the complete execution context including the final result, token usage, and metadata.

**nodes**: A list of Pydantic-AI graph nodes (`UserPromptNode`, `ModelRequestNode`, `CallToolsNode`) representing each step that occurred during the agent's execution. This provides visibility into what the agent did.

### Step 3: Access Results

```python
print(agent_run.result.output)
```

The result object comes directly from Pydantic-ai. For our translation example, it contains: "J'aime le café."

## Understanding Agent Execution

When you run an agent, Pydantic-ai orchestrates the following flow:

1. Your prompt is formatted with any system instructions and sent to the model
2. The model processes the input and generates a response
3. If the model calls tools, Pydantic-ai executes them and feeds results back to the model
4. This cycle continues until the model produces a final text response
5. Pydantic-ai returns the result along with complete execution metadata

This execution model is consistent across agentic frameworks. The specifics of APIs and abstractions differ, but the fundamental loop remains the same.

## Key Concepts Recap

**Agents** coordinate between language models, tools, and application logic. They manage conversation flow and execution until reaching a final result.

**Configuration as code** using YAML files is a best practice. It separates model selection from application logic, making code more maintainable and portable.

**Helper libraries** like ours reduce boilerplate without adding functionality. The actual agent work happens in Pydantic-ai. Our library just makes configuration easier.

**Execution transparency** through result objects and execution nodes lets you understand what your agent did, track costs, and debug issues.

In the following chapters, we'll explore more sophisticated patterns including tool use, multi-step reasoning, memory systems, and agent orchestration. All of these build on the foundation established here: creating agents, running them with prompts, and accessing results.
