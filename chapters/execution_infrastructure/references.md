## References

[Bubblewrap](https://github.com/containers/bubblewrap) -- Unprivileged sandboxing tool using Linux user namespaces. Used for lightweight process, filesystem, and network isolation without requiring root or a container runtime.

[Docker](https://docs.docker.com/) -- Container platform providing heavyweight process isolation with cgroup resource limits, full network namespace control, and image-based reproducibility. Used for production multi-tenant sandboxes and MCP server isolation.

[Envoy Proxy](https://www.envoyproxy.io/) -- High-performance edge/service proxy. Discussed as a design pattern for proxy-based selective network connectivity in sandbox environments handling confidential data.

[Project Jupyter](https://jupyter.org/) -- Open-source interactive computing platform. The notebook and cell model used in the REPL section borrows its metaphor and conventions (shared namespace, last-expression capture, `.ipynb` export).
