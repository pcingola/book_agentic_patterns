## Hands-On: AG-UI Frontend

This walkthrough covers the React frontend that connects to the AG-UI backend. The code is in `frontend/`.

### Dependencies

The frontend uses two AG-UI packages: `@ag-ui/client` provides `HttpAgent`, which speaks the AG-UI protocol (POST with `RunAgentInput`, SSE response stream). `@ag-ui/core` provides the TypeScript types (`Message`, `State`, etc.). No proprietary middleware or cloud service is involved -- `HttpAgent` talks directly to the backend.

### HttpAgent Setup

The `App` component creates an `HttpAgent` pointing at the backend URL. The agent is recreated via `useMemo` whenever the URL changes:

```tsx
import { HttpAgent } from '@ag-ui/client'
import type { State } from '@ag-ui/core'
import { useMemo, useState } from 'react'
import { ChatPanel } from './components/ChatPanel'
import { StatePanel } from './components/StatePanel'

const DEFAULT_BACKEND_URL = 'http://localhost:8000'

export default function App() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL)
  const [agentState, setAgentState] = useState<Record<string, unknown> | null>(null)

  const agent = useMemo(() => new HttpAgent({ url: backendUrl }), [backendUrl])

  return (
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
      <main>
        <ChatPanel agent={agent} backendUrl={backendUrl} onStateChange={(s: State) => setAgentState(s as Record<string, unknown>)} />
        <StatePanel state={agentState} />
      </main>
    </div>
  )
}
```

`HttpAgent` manages the conversation internally -- it tracks messages and state, builds the `RunAgentInput` payload, and parses the SSE event stream. The header input lets you change the backend URL at runtime, so you can switch between v1, v2, and v3 without restarting.

### ChatPanel Component

`ChatPanel` owns the chat interaction. On submit, it adds a user message to the agent, then calls `runAgent` with a subscriber that updates React state on each event:

```tsx
import { HttpAgent, randomUUID } from '@ag-ui/client'
import type { Message, State } from '@ag-ui/core'
import { useEffect, useRef, useState } from 'react'

interface ChatPanelProps {
  agent: HttpAgent
  backendUrl: string
  onStateChange: (state: State) => void
}

export function ChatPanel({ agent, backendUrl, onStateChange }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || isRunning) return

    setIsRunning(true)
    agent.addMessage({ id: randomUUID(), role: 'user', content: text })
    setMessages([...agent.messages])
    setInput('')

    try {
      await agent.runAgent({}, {
        onMessagesChanged({ messages }) {
          setMessages([...messages])
        },
        onStateChanged({ state }) {
          onStateChange(state)
        },
      })
    } catch (err) {
      console.error('Agent run failed:', err)
    } finally {
      setIsRunning(false)
    }
  }
  // ... render message list and input form
}
```

The flow works as follows. `agent.addMessage()` appends the user message to the agent's internal message list. `agent.runAgent()` POSTs a `RunAgentInput` (containing all messages and current state) to the backend URL, then streams back SSE events. As each event arrives, the SDK updates its internal state and fires the subscriber callbacks. `onMessagesChanged` fires on every text delta and tool call event, so the assistant's response streams into the UI in real time. `onStateChanged` fires on `StateSnapshotEvent`, pushing agent state updates to the `StatePanel`.

Messages are rendered by role: user messages are right-aligned blue bubbles, assistant messages are left-aligned gray bubbles, and tool messages appear as small monospace blocks. Assistant messages with tool calls display the function name and arguments.

### State Rendering

The `StatePanel` component receives agent state from the `onStateChanged` subscriber callback. When connected to v1 or v2 (no `StateDeps`), the panel shows "No state" because those backends never emit `StateSnapshotEvent`. When connected to v3, the panel updates as tools modify the `CalculatorState`.

This is the same concept as before but without any special hook -- the subscriber pattern gives direct control over how events update the UI.

### Key Takeaways

The frontend uses the standard AG-UI protocol directly via `HttpAgent`. The subscriber pattern (`onMessagesChanged`, `onStateChanged`) provides fine-grained control over how SSE events update the UI, with streaming text deltas and state snapshots handled through simple callbacks.
