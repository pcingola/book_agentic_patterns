import { CopilotKit, useCoAgentStateRender } from '@copilotkit/react-core'
import { CopilotChat } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'
import { useState } from 'react'
import { StatePanel } from './components/StatePanel'

const DEFAULT_BACKEND_URL = 'http://localhost:8000'

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
