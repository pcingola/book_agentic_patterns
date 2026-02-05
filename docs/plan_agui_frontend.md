# Plan: AG-UI Frontend Demo

## Objective

Build a React frontend using CopilotKit that connects to AG-UI backends. The purpose is educational: readers of the "Agentic Patterns" book should see a working agent UI and understand how CopilotKit connects to AG-UI backends.

## Tech Stack

- React 18+ with TypeScript
- Vite (fast setup, no CRA bloat)
- CopilotKit (`@copilotkit/react-core`, `@copilotkit/react-ui`)
- Tailwind CSS (optional, for quick styling)

## Requirements

### Functional

1. Connect to an AG-UI backend running on a configurable URL (default: `http://localhost:8000`)
2. Chat interface with message history
3. Display tool calls when agent uses tools
4. Display state updates when backend emits STATE_SNAPSHOT events
5. Work with all three example backends:
   - `example_agui_app_v1.py` - basic chat
   - `example_agui_app_v2.py` - chat with tools
   - `example_agui_app_v3.py` - chat with tools, state, and custom events

### Non-Functional

1. Minimal setup - readers should be able to run it quickly
2. Clean code that demonstrates CopilotKit patterns
3. Educational comments explaining key concepts

## Project Structure

```
agentic_patterns/examples/ui/frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── ChatPanel.tsx
│   │   └── StatePanel.tsx
│   └── styles/
│       └── index.css
└── README.md
```

## Implementation Steps

### 1. Project Setup

```bash
cd agentic_patterns/examples/ui
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @copilotkit/react-core @copilotkit/react-ui
npm install -D tailwindcss postcss autoprefixer  # optional
```

### 2. Main Entry (main.tsx)

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### 3. App Component (App.tsx)

```tsx
import { CopilotKit } from '@copilotkit/react-core'
import { CopilotChat } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'
import { useState } from 'react'
import { StatePanel } from './components/StatePanel'

const DEFAULT_BACKEND_URL = 'http://localhost:8000'

export default function App() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL)
  const [state, setState] = useState<Record<string, unknown> | null>(null)

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

        <main>
          <div className="chat-panel">
            <CopilotChat
              labels={{
                title: "Agent Chat",
                initial: "How can I help you?",
              }}
              onStateChange={(newState) => setState(newState)}
            />
          </div>

          <StatePanel state={state} />
        </main>
      </div>
    </CopilotKit>
  )
}
```

### 4. State Panel Component (components/StatePanel.tsx)

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

### 5. Styling (styles/index.css)

```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
}

header input {
  padding: 0.5rem;
  width: 300px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chat-panel {
  flex: 2;
  border-right: 1px solid #e0e0e0;
}

.state-panel {
  flex: 1;
  padding: 1rem;
  background: #f9f9f9;
  overflow: auto;
}

.state-panel h2 {
  margin-bottom: 1rem;
  font-size: 1rem;
  color: #666;
}

.state-panel pre {
  font-family: monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
}

.state-panel .empty {
  color: #999;
  font-style: italic;
}
```

## CopilotKit Configuration Notes

CopilotKit's `CopilotChat` component handles:
- Message input and display
- Streaming text responses
- Tool call visualization
- Conversation history

The `runtimeUrl` prop points to the AG-UI backend. CopilotKit speaks AG-UI natively.

For state synchronization with v3 backend, use the `onStateChange` callback or CopilotKit's state hooks to capture STATE_SNAPSHOT events.

## Running the Demo

### Terminal 1: Start backend

```bash
# For basic chat (v1)
uvicorn agentic_patterns.examples.ui.example_agui_app_v1:app --reload

# For tools (v2)
uvicorn agentic_patterns.examples.ui.example_agui_app_v2:app --reload

# For state management (v3)
uvicorn agentic_patterns.examples.ui.example_agui_app_v3:app --reload
```

### Terminal 2: Start frontend

```bash
cd agentic_patterns/examples/ui/frontend
npm run dev
```

Open http://localhost:5173 in browser.

## Testing Checklist

- [ ] v1 backend: Send "Hello", verify streaming response
- [ ] v2 backend: Ask "What is 2 + 3?", verify tool call shown
- [ ] v3 backend: Do calculations, verify state panel updates with history
- [ ] Change backend URL in UI, verify reconnection works

## CORS Configuration

The AG-UI backends need CORS enabled for the frontend to connect. Add to each example:

```python
from fastapi.middleware.cors import CORSMiddleware

# After creating app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Or wrap the AGUIApp in a FastAPI app with CORS middleware.

## File Location

```
agentic_patterns/examples/ui/frontend/
```

## Out of Scope

- Authentication
- Persistent storage
- Mobile responsiveness
- Production deployment
- Custom theming beyond basic layout
