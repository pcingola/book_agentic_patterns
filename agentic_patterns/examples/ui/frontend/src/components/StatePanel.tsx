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
