## Hands-On: AG-UI Frontend

This walkthrough covers the React frontend that connects to the AG-UI backend. The code is in `frontend/`.

### CopilotKit Provider

CopilotKit is the AG-UI client library for React. The `App` component wraps everything in a `CopilotKit` provider that points to the backend URL:

```tsx
import { CopilotKit, useCoAgentStateRender } from '@copilotkit/react-core'
import { CopilotChat } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'
import { useState } from 'react'
import { StatePanel } from './components/StatePanel'

const DEFAULT_BACKEND_URL = 'http://localhost:8000'

export default function App() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL)

  return (
    <CopilotKit runtimeUrl={backendUrl}>
      <div className="app-container">
        <header>
          <h1>AG-UI Demo</h1>
          <input
            type="text"
            value={backendUrl}
            onChange={(e) => setBackendUrl(e.target.value)}
            placeholder="Backend URL"
          />
        </header>
        <ChatWithState />
      </div>
    </CopilotKit>
  )
}
```

The `runtimeUrl` prop is the only configuration CopilotKit needs -- it handles the AG-UI protocol (SSE connection, event parsing, message rendering) under the hood. The text input in the header lets you change the backend URL at runtime, which becomes useful for switching between v1, v2, and v3.

### Chat Component

The `ChatWithState` component combines the chat UI with state rendering:

```tsx
function ChatWithState() {
  const [agentState, setAgentState] = useState<Record<string, unknown> | null>(null)

  useCoAgentStateRender({
    name: 'agent_state',
    render: ({ state }: { state: unknown }) => {
      setAgentState(state as Record<string, unknown>)
      return null
    },
  })

  return (
    <main>
      <div className="chat-panel">
        <CopilotChat
          labels={{
            title: 'Agent Chat',
            initial: 'How can I help you?',
          }}
        />
      </div>
      <StatePanel state={agentState} />
    </main>
  )
}
```

`CopilotChat` renders the chat interface -- message bubbles, input field, streaming text. The `useCoAgentStateRender` hook listens for `StateSnapshotEvent` from the AG-UI stream and captures the state object whenever it arrives.

### State Rendering

The `StatePanel` component displays the agent state:

```tsx
interface StatePanelProps {
  state: Record<string, unknown> | null
}

export function StatePanel({ state }: StatePanelProps) {
  if (!state || Object.keys(state).length === 0) {
    return (
      <aside className="state-panel">
        <h2>State</h2>
        <p className="empty">No state (backend v1/v2)</p>
      </aside>
    )
  }

  return (
    <aside className="state-panel">
      <h2>State</h2>
      <pre>{JSON.stringify(state, null, 2)}</pre>
    </aside>
  )
}
```

When connected to v1 or v2 (no `StateDeps`), the panel shows "No state" because those backends never emit `StateSnapshotEvent`. When connected to v3, the panel updates in real time as tools modify the `CalculatorState`, showing history entries and the last result as pretty-printed JSON.

### Key Takeaways

CopilotKit acts as the AG-UI client, translating the SSE event stream into React components. The only configuration is the backend URL.

The `useCoAgentStateRender` hook bridges `StateSnapshotEvent` from the protocol into React state, enabling real-time UI updates driven by agent tools.
