# Durable Execution

Pydantic AI allows you to build durable agents that can preserve their progress across transient API failures and application errors or restarts, and handle long-running, asynchronous, and human-in-the-loop workflows with production-grade reliability. Durable agents have full support for [streaming](https://ai.pydantic.dev/agent/#streaming-all-events) and [MCP](https://ai.pydantic.dev/mcp/client/index.md), with the added benefit of fault tolerance.

Pydantic AI natively supports three durable execution solutions:

- [Temporal](https://ai.pydantic.dev/durable_execution/temporal/index.md)
- [DBOS](https://ai.pydantic.dev/durable_execution/dbos/index.md)
- [Prefect](https://ai.pydantic.dev/durable_execution/prefect/index.md)

These integrations only use Pydantic AI's public interface, so they also serve as a reference for integrating with other durable systems.
