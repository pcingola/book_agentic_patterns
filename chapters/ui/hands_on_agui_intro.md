## Hands-On: AG-UI Introduction

This hands-on builds a chat application where a PydanticAI agent runs on the backend and a React frontend connects to it via the AG-UI protocol. Three backend versions progress from a minimal agent to tools to state management, while the same frontend works unchanged against all three.

The code is in `agentic_patterns/examples/ui/`. Backend examples are `example_agui_app_v1.py`, `example_agui_app_v2.py`, and `example_agui_app_v3.py`. The frontend is in `frontend/`.

### Architecture

The backend is an ASGI application that exposes a PydanticAI agent via the AG-UI protocol over HTTP with Server-Sent Events (SSE). The frontend is a React application that uses CopilotKit as the AG-UI client library to consume that event stream and render the chat UI.

The two sides communicate through a single HTTP endpoint. The frontend sends a POST request with the conversation messages; the backend runs the agent and streams events back: run lifecycle (started/finished), text deltas as the model generates tokens, tool call events, state snapshots, and custom events. The frontend interprets these events and updates the UI accordingly.

Because they communicate through the AG-UI protocol, backend and frontend are fully decoupled. You can evolve the agent independently of the UI, or swap frontends without touching agent code.

### Running the Backend

AG-UI applications are ASGI apps run with uvicorn. Start any of the three versions:

```bash
uvicorn agentic_patterns.examples.ui.example_agui_app_v1:app --reload  # minimal
uvicorn agentic_patterns.examples.ui.example_agui_app_v2:app --reload  # with tools
uvicorn agentic_patterns.examples.ui.example_agui_app_v3:app --reload  # with state
```

This starts an HTTP server on port 8000.

### Testing with curl

Before connecting a frontend, you can test the endpoint directly:

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId": "thread-1",
    "runId": "run-1",
    "state": {},
    "messages": [{"id": "msg-1", "role": "user", "content": "What is 2 + 2?"}],
    "tools": [],
    "context": [],
    "forwardedProps": {}
  }'
```

The response is a stream of Server-Sent Events: run started, text message deltas as the model generates tokens, and run finished. This is the raw protocol that frontends consume.

### Running the Frontend

Install dependencies and start the development server:

```bash
cd agentic_patterns/examples/ui/frontend
npm install
npm run dev
```

Vite serves the frontend on `http://localhost:5173`. Both frontend and backend must be running simultaneously.

### Swapping Backends

The same frontend works unchanged against all three backend versions. With v1, you get a plain chat. With v2, tool calls appear in the conversation. With v3, the state panel comes alive. The frontend has a text input in the header that lets you change the backend URL at runtime, making it easy to switch between versions without restarting.

No frontend code changes needed -- the protocol handles everything.
