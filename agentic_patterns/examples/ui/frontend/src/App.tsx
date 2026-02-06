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
        <ChatPanel agent={agent} onStateChange={(s: State) => setAgentState(s as Record<string, unknown>)} />
        <StatePanel state={agentState} />
      </main>
    </div>
  )
}
