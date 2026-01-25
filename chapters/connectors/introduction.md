## Introduction

Connectors are the boundary layer through which agentic systems observe, query, and act upon external data sources, translating heterogeneous systems into a small set of predictable interaction models.

At scale, connectors are not primarily a question of protocols or APIs, but of *abstraction*. An agent does not reason about JDBC versus REST, or CSV versus JSON; it reasons about whether it can ask a question, invoke an operation, or read and modify a piece of content. A well-designed connector layer therefore serves two purposes simultaneously. First, it constrains how agents interact with external systems so that behavior is safe, auditable, and reproducible. Second, it reduces cognitive and implementation complexity by collapsing a wide variety of integrations into a small number of stable patterns.

This chapter treats connectors as first-class architectural components. Rather than cataloging integrations product by product, it focuses on the underlying interaction patterns that recur across databases, SaaS platforms, file systems, and code repositories. Later sections will explore specific connector families such as SQL, OpenAPI-based APIs, file formats, and SaaS tools, but all of them build on the same foundational ideas introduced here.

