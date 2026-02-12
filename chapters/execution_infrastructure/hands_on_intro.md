## Hands-On: Introduction

The hands-on exercise that follows demonstrates MCP server isolation -- the pattern of running dual server instances with automatic client-side switching based on data sensitivity. The exercise uses a template MCP server that exercises several production concerns in a single flow: workspace path translation, large-result truncation, tool permissions, error classification, compliance flagging, and server-to-client log forwarding.

The earlier sections of this chapter covered the isolation primitives (sandbox, REPL, network control) and the design patterns for applying them to MCP servers and skill scripts. The hands-on brings the MCP isolation pattern to life with a runnable notebook where you can observe the client switching from a normal server instance to an isolated one after private data enters the session.
