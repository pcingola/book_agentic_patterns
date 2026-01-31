## Introduction

Connectors are tools that agents use directly at runtime to observe, query, and act upon external data sources. Unlike traditional libraries or SDKs written for programmers, connectors are designed to be invoked by the agent itself as it reasons through a task. The agent decides when to call a connector, what parameters to pass, and how to interpret the results. Your role as a developer is to expose these connectors to the agent and configure appropriate permissions; the agent handles the rest.

This distinction matters because it shifts where complexity lives. A programmer integrating a database might write code that handles connection pooling, query construction, and result parsing. An agent using a database connector simply calls a tool like `query_database(sql="SELECT ...")` and receives structured results. The connector encapsulates the mechanical details so the agent can focus on the task at hand.

At scale, connectors are not primarily a question of protocols or APIs, but of *abstraction*. An agent does not reason about JDBC versus REST, or CSV versus JSON; it reasons about whether it can ask a question, invoke an operation, or read and modify a piece of content. A well-designed connector layer therefore serves two purposes simultaneously. First, it constrains how agents interact with external systems so that behavior is safe, auditable, and reproducible. Second, it reduces cognitive and implementation complexity by collapsing a wide variety of integrations into a small number of stable patterns.

This chapter treats connectors as first-class architectural components. Rather than cataloging integrations product by product, it focuses on the underlying interaction patterns that recur across databases, SaaS platforms, file systems, and code repositories. Later sections will explore specific connector families such as SQL, OpenAPI-based APIs, file formats, and SaaS tools, but all of them build on the same foundational ideas introduced here.

