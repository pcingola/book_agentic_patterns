## Hands-On: AG-UI User Feedback

User feedback follows the same side-channel pattern as file uploads. AG-UI has no built-in mechanism for ratings or annotations, so a separate REST endpoint handles feedback submission while the event stream continues to carry text, tool calls, and state.

### The /feedback endpoint

The v5 backend extends v4 by adding a `/feedback` route alongside the existing `/upload` route:

```python
from agentic_patterns.core.feedback import FeedbackType, add_feedback

DEMO_USER_ID = "demo"
DEMO_SESSION_ID = "agui"

async def feedback_handler(request: Request) -> JSONResponse:
    """Handle user feedback (thumbs up/down, comments)."""
    body = await request.json()
    feedback_type_str = body.get("feedback_type")
    comment = body.get("comment", "")

    try:
        feedback_type = FeedbackType(feedback_type_str)
    except (ValueError, KeyError):
        return JSONResponse({"error": f"Invalid feedback_type: {feedback_type_str}"}, status_code=400)

    add_feedback(feedback_type, comment=comment, user_id=DEMO_USER_ID, session_id=DEMO_SESSION_ID)
    return JSONResponse({"status": "ok"})
```

The handler validates the `feedback_type` field against the `FeedbackType` enum (which accepts `thumbs_up`, `thumbs_down`, `error_report`, `comment`) and delegates to `add_feedback()` from the core feedback module. The core module appends a timestamped `FeedbackEntry` to a per-session JSON file under `FEEDBACK_DIR / user_id / session_id / feedback.json`.

The user and session IDs are hardcoded for the demo. In a production system, these would come from JWT claims decoded at the request boundary -- the same identity propagation pattern described in the session propagation section.

Both routes are registered in the `AGUIApp` constructor:

```python
app = AGUIApp(
    agent,
    deps=StateDeps(CalculatorState()),
    routes=[
        Route('/upload', upload_handler, methods=['POST']),
        Route('/feedback', feedback_handler, methods=['POST']),
    ],
)
```

### Frontend changes

The `ChatPanel` component adds two things: a `feedbackGiven` state that tracks which messages have been rated, and a `submitFeedback` function that POSTs to the backend.

```tsx
const [feedbackGiven, setFeedbackGiven] = useState<Record<string, string>>({})

async function submitFeedback(messageId: string, feedbackType: string) {
  setFeedbackGiven((prev) => ({ ...prev, [messageId]: feedbackType }))
  try {
    await fetch(`${backendUrl}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback_type: feedbackType }),
    })
  } catch (err) {
    console.error('Feedback submission failed:', err)
  }
}
```

The state update happens before the network call so the UI responds immediately. If the POST fails, the buttons stay in their rated state -- a pragmatic choice for a demo. Production code would roll back on error.

Each assistant message renders two small buttons below its content:

```tsx
{msg.role === 'assistant' && (
  <div className="feedback-buttons">
    <button
      className={`feedback-btn${feedbackGiven[msg.id] === 'thumbs_up' ? ' active' : ''}`}
      onClick={() => submitFeedback(msg.id, 'thumbs_up')}
      disabled={!!feedbackGiven[msg.id]}
      title="Thumbs up"
    >+1</button>
    <button
      className={`feedback-btn${feedbackGiven[msg.id] === 'thumbs_down' ? ' active' : ''}`}
      onClick={() => submitFeedback(msg.id, 'thumbs_down')}
      disabled={!!feedbackGiven[msg.id]}
      title="Thumbs down"
    >-1</button>
  </div>
)}
```

Once a button is clicked, both buttons are disabled and the selected one is highlighted. The `feedbackGiven` record maps message IDs to the chosen feedback type, so the component knows which button to highlight and that no further clicks should be accepted for that message.

### The side-channel pattern, generalized

File uploads and user feedback are both examples of the same architectural idea: when the protocol does not support an interaction natively, add a REST endpoint as a side-channel. The AG-UI event stream handles what it was designed for (text streaming, tool calls, state snapshots), and everything else goes through standard HTTP.

This pattern scales to other concerns that sit outside the conversation stream: analytics events, preference toggles, session metadata updates, or audit logging. Each one gets its own endpoint on the same Starlette application, keeping the AG-UI adapter layer clean and focused.
