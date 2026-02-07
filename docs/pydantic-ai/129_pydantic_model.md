# Pydantic Model

Simple example of using Pydantic AI to construct a Pydantic model from a text input.

Demonstrates:

- [structured `output_type`](https://ai.pydantic.dev/output/#structured-output)

## Running the Example

With [dependencies installed and environment variables set](https://ai.pydantic.dev/examples/setup/#usage), run:

```bash
python -m pydantic_ai_examples.pydantic_model
```

```bash
uv run -m pydantic_ai_examples.pydantic_model
```

This examples uses `openai:gpt-5` by default, but it works well with other models, e.g. you can run it with Gemini using:

```bash
PYDANTIC_AI_MODEL=gemini-3-pro-preview python -m pydantic_ai_examples.pydantic_model
```

```bash
PYDANTIC_AI_MODEL=gemini-3-pro-preview uv run -m pydantic_ai_examples.pydantic_model
```

(or `PYDANTIC_AI_MODEL=gemini-3-flash-preview ...`)

## Example Code

[pydantic_model.py](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/pydantic_model.py)

```python
"""Simple example of using Pydantic AI to construct a Pydantic model from a text input.

Run with:

    uv run -m pydantic_ai_examples.pydantic_model
"""

import os

import logfire
from pydantic import BaseModel

from pydantic_ai import Agent

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic_ai()


class MyModel(BaseModel):
    city: str
    country: str


model = os.getenv('PYDANTIC_AI_MODEL', 'openai:gpt-5.2')
print(f'Using model: {model}')
agent = Agent(model, output_type=MyModel)

if __name__ == '__main__':
    result = agent.run_sync('The windy city in the US of A.')
    print(result.output)
    print(result.usage())
```
