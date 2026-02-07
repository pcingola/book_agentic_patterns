# HttpAgent
Source: https://docs.ag-ui.com/sdk/js/client/http-agent

HTTP-based agent for connecting to remote AI agents

# HttpAgent

The `HttpAgent` extends `AbstractAgent` to provide HTTP-based connectivity to
remote AI agents. It handles the request/response cycle and transforms the HTTP
event stream into standard Agent User Interaction Protocol events.

```typescript theme={null}
import { HttpAgent } from "@ag-ui/client"
```

## Configuration

When creating an HTTP agent, you need to provide an `HttpAgentConfig` object:

```typescript theme={null}
interface HttpAgentConfig extends AgentConfig {
  url: string // Endpoint URL for the agent service
  headers?: Record<string, string> // Optional HTTP headers
}
```

## Creating an HttpAgent

```typescript theme={null}
const agent = new HttpAgent({
  url: "https://api.example.com/v1/agent",
  headers: {
    Authorization: "Bearer your-api-key",
  },
})
```

## Methods

### runAgent()

Executes the agent by making an HTTP request to the configured endpoint.

```typescript theme={null}
runAgent(parameters?: RunAgentParameters, subscriber?: AgentSubscriber): Promise<RunAgentResult>
```

#### Parameters

The `parameters` argument follows the standard `RunAgentParameters` interface.
The optional `subscriber` parameter allows you to provide an
[AgentSubscriber](/sdk/js/client/subscriber) for handling events during this
specific run.

#### Return Value

```typescript theme={null}
interface RunAgentResult {
  result: any // The final result returned by the agent
  newMessages: Message[] // New messages added during this run
}
```

### subscribe()

Adds an [AgentSubscriber](/sdk/js/client/subscriber) to handle events across
multiple agent runs.

```typescript theme={null}
subscribe(subscriber: AgentSubscriber): { unsubscribe: () => void }
```

Returns an object with an `unsubscribe()` method to remove the subscriber when
no longer needed.

### abortRun()

Cancels the current HTTP request using the AbortController.

```typescript theme={null}
abortRun(): void
```

## Protected Methods

### requestInit()

Configures the HTTP request. Override this method to customize how requests are
made.

```typescript theme={null}
protected requestInit(input: RunAgentInput): RequestInit
```

Default implementation:

```typescript theme={null}
{
  method: "POST",
  headers: {
    ...this.headers,
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  },
  body: JSON.stringify(input),
  signal: this.abortController.signal,
}
```

### run()

Implements the abstract `run()` method from `AbstractAgent` using HTTP requests.

```typescript theme={null}
run(input: RunAgentInput): RunAgent
```

## Properties

* `url`: The endpoint URL for the agent service
* `headers`: HTTP headers to include with requests
* `abortController`: AbortController instance for request cancellation
