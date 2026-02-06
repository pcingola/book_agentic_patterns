# Plan: Replace CopilotKit with AG-UI client

## Problem

The frontend uses CopilotKit (`@copilotkit/react-core`, `@copilotkit/react-ui`) which wraps AG-UI requests in a proprietary `{method, params, body}` envelope via `runtimeUrl`. The backend (`pydantic_ai.ui.ag_ui.app.AGUIApp`) expects standard AG-UI protocol where `RunAgentInput` is the POST body directly. This causes 422 Unprocessable Entity on every request.

CopilotKit's `runtimeUrl` requires a CopilotKit Runtime middleware server between frontend and agent. The only workaround is `agents__unsafe_dev_only`, a dev-only prop designed to push users toward CopilotKit Cloud. This is inappropriate for a book teaching standard AG-UI.

## Solution

Drop CopilotKit entirely. Use `@ag-ui/client` (the standard AG-UI JavaScript SDK) with a simple React chat UI. `HttpAgent` handles all protocol work: builds `RunAgentInput`, sends it as POST body, parses the SSE event stream. We build a thin chat component on top.

## AG-UI client API summary

```typescript
import { HttpAgent, randomUUID } from '@ag-ui/client'
import type { Message } from '@ag-ui/core'

const agent = new HttpAgent({ url: 'http://localhost:8000' })

// Add a user message
agent.addMessage({ id: randomUUID(), role: 'user', content: 'hello' })

// Run the agent. Subscriber callbacks fire during streaming.
await agent.runAgent({}, {
  onMessagesChanged({ messages }) { /* update React state with messages */ },
  onStateChanged({ state }) { /* update state panel */ },
})

// agent.messages contains the full conversation after the run
```

`HttpAgent.runAgent()` builds `RunAgentInput` from `agent.messages` and `agent.state`, POSTs it to the URL, and streams back SSE events. The `onMessagesChanged` callback fires after each event updates the message list (text deltas accumulate into the assistant message automatically by the SDK).

## Step 1: Update `package.json`

File: `agentic_patterns/examples/ui/frontend/package.json`

Remove from dependencies:
- `@copilotkit/react-core`
- `@copilotkit/react-ui`

Add to dependencies:
- `@ag-ui/client`
- `@ag-ui/core`

Keep everything else (react, react-dom, vite, typescript, all devDependencies).

Run `npm install`.

## Step 2: Rewrite `src/App.tsx`

File: `agentic_patterns/examples/ui/frontend/src/App.tsx`

Remove all CopilotKit imports. New structure:

```
App
  header -- backend URL input (keep existing behavior)
  main
    ChatPanel (new, see step 3)
    StatePanel (existing, unchanged)
```

App creates `HttpAgent` via `useMemo` (recreate when backendUrl changes). Holds `agentState` in a `useState`. Passes agent + state setter to `ChatPanel`, passes `agentState` to `StatePanel`.

## Step 3: Create `src/components/ChatPanel.tsx`

New file: `agentic_patterns/examples/ui/frontend/src/components/ChatPanel.tsx`

Props: `{ agent: HttpAgent, onStateChange: (state) => void }`

Local state:
- `messages: Message[]` -- mirrors `agent.messages`
- `input: string` -- text input value
- `isRunning: boolean` -- disables send during execution

On submit:
1. Set `isRunning = true`
2. `agent.addMessage({ id: randomUUID(), role: 'user', content: input })`
3. Set `messages` from `agent.messages` (shows user message immediately)
4. Clear input
5. `await agent.runAgent({}, { onMessagesChanged({ messages }) { setMessages([...messages]) }, onStateChanged({ state }) { onStateChange(state) } })`
6. Set `isRunning = false`

Rendering:
- Scrollable message list, auto-scroll to bottom on new messages
- Each message rendered by role: `user` right-aligned, `assistant` left-aligned, `tool` as small muted block
- `assistant` message content streams in live (onMessagesChanged fires on each text delta)
- Input bar at bottom: text input + send button, disabled when `isRunning`

Import `randomUUID` from `@ag-ui/client`.

## Step 4: Keep `src/components/StatePanel.tsx`

No changes. It already takes `state: Record<string, unknown> | null` and renders JSON.

## Step 5: Update `src/styles/index.css`

Add styles for chat messages (user/assistant bubbles, tool result blocks, message list scroll, input bar). Keep existing header, layout, and state-panel styles.

## Step 6: No backend changes

`example_agui_app_v1.py` (and v2, v3) already serve standard AG-UI protocol correctly. The backend is not the problem.

## Step 7: Update `chapters/ui/hands_on_agui_intro.md`

Replace all CopilotKit references:

- In the Architecture section, replace "uses CopilotKit as the AG-UI client library" with "uses the `@ag-ui/client` SDK (HttpAgent)" or similar. Explain that HttpAgent sends `RunAgentInput` as the POST body and receives SSE events.
- The curl test section stays as-is (it already shows the raw protocol).
- The "Running the Frontend" and "Swapping Backends" sections need no structural changes, just remove any CopilotKit mentions if present.

## Step 8: Rewrite `chapters/ui/hands_on_agui_frontend.md`

This file is entirely CopilotKit-centric and needs a full rewrite. Replace with content that covers:

1. **Dependencies**: `@ag-ui/client` and `@ag-ui/core` instead of CopilotKit packages.
2. **HttpAgent setup**: Show how `App` creates `HttpAgent` with the backend URL. Explain that `HttpAgent` speaks standard AG-UI protocol (POST with `RunAgentInput`, SSE response).
3. **ChatPanel component**: Show the submit flow (addMessage, runAgent with subscriber). Explain how `onMessagesChanged` fires on each SSE event, giving streaming updates. Show how message roles map to UI rendering.
4. **State rendering**: Explain how `onStateChanged` in the subscriber captures `StateSnapshotEvent` and feeds it to `StatePanel`. Same concept as before, just without the `useCoAgentStateRender` hook.
5. **Key takeaways**: The frontend uses standard AG-UI protocol directly via `HttpAgent`. No proprietary middleware or cloud service required. The subscriber pattern gives fine-grained control over how events update the UI.

## Step 9: Review `chapters/ui/hands_on_agui_backend.md`

Minimal changes. Scan for any CopilotKit mentions (there shouldn't be many since this file focuses on the Python backend). The "Key Takeaways" section at the bottom says "AG-UI is a protocol, not a framework" which is correct and stays.

## Verification

1. `cd agentic_patterns/examples/ui/frontend && npm install && npm run dev`
2. `uvicorn agentic_patterns.examples.ui.example_agui_app_v1:app --reload`
3. Open `http://localhost:5173`, send a message, verify streaming response without 422.
4. Test against v2 (tool calls visible) and v3 (state panel updates).
