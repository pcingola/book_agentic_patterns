# Overview
Source: https://docs.ag-ui.com/sdk/python/core/overview

Core concepts in the Agent User Interaction Protocol SDK

```bash theme={null}
pip install ag-ui-protocol
```

# ag\_ui.core

The Agent User Interaction Protocol SDK uses a streaming event-based
architecture with strongly typed data structures. This package provides the
foundation for connecting to agent systems.

```python theme={null}
from ag_ui.core import ...
```

## Types

Core data structures that represent the building blocks of the system:

* [RunAgentInput](/sdk/python/core/types#runagentinput) - Input parameters for
  running agents
* [Message](/sdk/python/core/types#message-types) - User assistant communication
  and tool usage
* [Context](/sdk/python/core/types#context) - Contextual information provided to
  agents
* [Tool](/sdk/python/core/types#tool) - Defines functions that agents can call
* [State](/sdk/python/core/types#state) - Agent state management

<Card title="Types Reference" icon="cube" href="/sdk/python/core/types">
  Complete documentation of all types in the ag\_ui.core package
</Card>

## Events

Events that power communication between agents and frontends:

* [Lifecycle Events](/sdk/python/core/events#lifecycle-events) - Run and step
  tracking
* [Text Message Events](/sdk/python/core/events#text-message-events) - Assistant
  message streaming
* [Tool Call Events](/sdk/python/core/events#tool-call-events) - Function call
  lifecycle
* [State Management Events](/sdk/python/core/events#state-management-events) -
  Agent state updates
* [Special Events](/sdk/python/core/events#special-events) - Raw and custom
  events

<Card title="Events Reference" icon="cube" href="/sdk/python/core/events">
  Complete documentation of all events in the ag\_ui.core package
</Card>
