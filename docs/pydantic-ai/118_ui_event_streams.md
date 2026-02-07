# UI Event Streams

If you're building a chat app or other interactive frontend for an AI agent, your backend will need to receive agent run input (like a chat message or complete [message history](https://ai.pydantic.dev/message-history/index.md)) from the frontend, and will need to stream the [agent's events](https://ai.pydantic.dev/agent/#streaming-all-events) (like text, thinking, and tool calls) to the frontend so that the user knows what's happening in real time.

While your frontend could use Pydantic AI's ModelRequest and AgentStreamEvent directly, you'll typically want to use a UI event stream protocol that's natively supported by your frontend framework.

Pydantic AI natively supports two UI event stream protocols:

- [Agent-User Interaction (AG-UI) Protocol](https://ai.pydantic.dev/ui/ag-ui/index.md)
- [Vercel AI Data Stream Protocol](https://ai.pydantic.dev/ui/vercel-ai/index.md)

These integrations are implemented as subclasses of the abstract UIAdapter class, so they also serve as a reference for integrating with other UI event stream protocols.

## Usage

The protocol-specific UIAdapter subclass (i.e. AGUIAdapter or VercelAIAdapter) is responsible for transforming agent run input received from the frontend into arguments for [`Agent.run_stream_events()`](https://ai.pydantic.dev/agent/#running-agents), running the agent, and then transforming Pydantic AI events into protocol-specific events. The event stream transformation is handled by a protocol-specific UIEventStream subclass, but you typically won't use this directly.

If you're using a Starlette-based web framework like FastAPI, you can use the UIAdapter.dispatch_request() class method from an endpoint function to directly handle a request and return a streaming response of protocol-specific events. This is demonstrated in the next section.

If you're using a web framework not based on Starlette (e.g. Django or Flask) or need fine-grained control over the input or output, you can create a `UIAdapter` instance and directly use its methods. This is demonstrated in "Advanced Usage" section below.

### Usage with Starlette/FastAPI

Besides the request, UIAdapter.dispatch_request() takes the agent, the same optional arguments as [`Agent.run_stream_events()`](https://ai.pydantic.dev/agent/#running-agents), and an optional `on_complete` callback function that receives the completed AgentRunResult and can optionally yield additional protocol-specific events.

Note

These examples use the `VercelAIAdapter`, but the same patterns apply to all `UIAdapter` subclasses.

[Learn about Gateway](https://ai.pydantic.dev/gateway) dispatch_request.py

```python
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from pydantic_ai import Agent
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

agent = Agent('gateway/openai:gpt-5.2')

app = FastAPI()

@app.post('/chat')
async def chat(request: Request) -> Response:
    return await VercelAIAdapter.dispatch_request(request, agent=agent)
```

dispatch_request.py

```python
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from pydantic_ai import Agent
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

agent = Agent('openai:gpt-5.2')

app = FastAPI()

@app.post('/chat')
async def chat(request: Request) -> Response:
    return await VercelAIAdapter.dispatch_request(request, agent=agent)
```

### Advanced Usage

If you're using a web framework not based on Starlette (e.g. Django or Flask) or need fine-grained control over the input or output, you can create a `UIAdapter` instance and directly use its methods, which can be chained to accomplish the same thing as the `UIAdapter.dispatch_request()` class method shown above:

1. The UIAdapter.build_run_input() class method takes the request body as bytes and returns a protocol-specific run input object, which you can then pass to the UIAdapter() constructor along with the agent.
   - You can also use the UIAdapter.from_request() class method to build an adapter directly from a Starlette/FastAPI request.
1. The UIAdapter.run_stream() method runs the agent and returns a stream of protocol-specific events. It supports the same optional arguments as [`Agent.run_stream_events()`](https://ai.pydantic.dev/agent/#running-agents) and an optional `on_complete` callback function that receives the completed AgentRunResult and can optionally yield additional protocol-specific events.
   - You can also use UIAdapter.run_stream_native() to run the agent and return a stream of Pydantic AI events instead, which can then be transformed into protocol-specific events using UIAdapter.transform_stream().
1. The UIAdapter.encode_stream() method encodes the stream of protocol-specific events as SSE (HTTP Server-Sent Events) strings, which you can then return as a streaming response.
   - You can also use UIAdapter.streaming_response() to generate a Starlette/FastAPI streaming response directly from the protocol-specific event stream returned by `run_stream()`.

Note

This example uses FastAPI, but can be modified to work with any web framework.

[Learn about Gateway](https://ai.pydantic.dev/gateway) run_stream.py

```python
import json
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError

from pydantic_ai import Agent
from pydantic_ai.ui import SSE_CONTENT_TYPE
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

agent = Agent('gateway/openai:gpt-5.2')

app = FastAPI()


@app.post('/chat')
async def chat(request: Request) -> Response:
    accept = request.headers.get('accept', SSE_CONTENT_TYPE)
    try:
        run_input = VercelAIAdapter.build_run_input(await request.body())
    except ValidationError as e:
        return Response(
            content=json.dumps(e.json()),
            media_type='application/json',
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    adapter = VercelAIAdapter(agent=agent, run_input=run_input, accept=accept)
    event_stream = adapter.run_stream()

    sse_event_stream = adapter.encode_stream(event_stream)
    return StreamingResponse(sse_event_stream, media_type=accept)
```

run_stream.py

```python
import json
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError

from pydantic_ai import Agent
from pydantic_ai.ui import SSE_CONTENT_TYPE
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

agent = Agent('openai:gpt-5.2')

app = FastAPI()


@app.post('/chat')
async def chat(request: Request) -> Response:
    accept = request.headers.get('accept', SSE_CONTENT_TYPE)
    try:
        run_input = VercelAIAdapter.build_run_input(await request.body())
    except ValidationError as e:
        return Response(
            content=json.dumps(e.json()),
            media_type='application/json',
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    adapter = VercelAIAdapter(agent=agent, run_input=run_input, accept=accept)
    event_stream = adapter.run_stream()

    sse_event_stream = adapter.encode_stream(event_stream)
    return StreamingResponse(sse_event_stream, media_type=accept)
```
