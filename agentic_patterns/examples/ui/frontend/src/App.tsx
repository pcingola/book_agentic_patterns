import { HttpAgent } from '@ag-ui/client'
import type { State } from '@ag-ui/core'
import { useEffect, useMemo, useState } from 'react'
import { ChatPanel } from './components/ChatPanel'
import { StatePanel } from './components/StatePanel'

const DEFAULT_BACKEND_URL = 'http://localhost:8000'

function getInitialDark(): boolean {
  const stored = localStorage.getItem('theme')
  if (stored) return stored === 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export default function App() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL)
  const [agentState, setAgentState] = useState<Record<string, unknown> | null>(null)
  const [dark, setDark] = useState(getInitialDark)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

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
        <button className="theme-toggle" onClick={() => setDark(!dark)} title="Toggle dark mode">
          {dark ? '\u2600' : '\u263E'}
        </button>
      </header>
      <main>
        <ChatPanel agent={agent} onStateChange={(s: State) => setAgentState(s as Record<string, unknown>)} />
        <StatePanel state={agentState} />
      </main>
    </div>
  )
}
