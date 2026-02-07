# Overview
Source: https://docs.ag-ui.com/sdk/js/core/overview

Core concepts in the Agent User Interaction Protocol SDK

# @ag-ui/core

The Agent User Interaction Protocol SDK uses a streaming event-based
architecture with strongly typed data structures. This package provides the
foundation for connecting to agent systems.

```bash theme={null}
npm install @ag-ui/core
```

## Types

Core data structures that represent the building blocks of the system:

* [RunAgentInput](/sdk/js/core/types#runagentinput) - Input parameters for
  running agents
* [Message](/sdk/js/core/types#message-types) - User assistant communication and
  tool usage
* [Context](/sdk/js/core/types#context) - Contextual information provided to
  agents
* [Tool](/sdk/js/core/types#tool) - Defines functions that agents can call
* [State](/sdk/js/core/types#state) - Agent state management

<Card title="Types Reference" icon="cube" href="/sdk/js/core/types">
  Complete documentation of all types in the @ag-ui/core package
</Card>

## Events

Events that power communication between agents and frontends:

* [Lifecycle Events](/sdk/js/core/events#lifecycle-events) - Run and step
  tracking
* [Text Message Events](/sdk/js/core/events#text-message-events) - Assistant
  message streaming
* [Tool Call Events](/sdk/js/core/events#tool-call-events) - Function call
  lifecycle
* [State Management Events](/sdk/js/core/events#state-management-events) - Agent
  state updates
* [Special Events](/sdk/js/core/events#special-events) - Raw and custom events

<Card title="Events Reference" icon="cube" href="/sdk/js/core/events">
  Complete documentation of all events in the @ag-ui/core package
</Card>
