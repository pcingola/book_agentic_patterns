# To do

- Tool contracts and schemas `tool_contracts_schemas.md`: 
  - "Explicit termination via final schemas" (Langchain is like this as well?)
  - "Retries as part of the contract": Pydantic-AI is not like this: "Errors can be marked as retryable or fatal, allowing the model to reason explicitly about recovery. Because retries are mediated through the same schema, repeated calls remain safe, auditable, and deterministic."

- `tool_permissions.md`: 
  - BEST PRACTICE: Most tolls use read only roles (e.g. SQL databases)
  - BEST PRACTICE: Use SAS that have ZDR (Zero Data Retention) enabled

- `the_workspace.md`:
  - "Multi-modal tools and the workspace": "....do not fit cleanly into textual prompts" => Can quickly fill the prompt (return a smaller image, or a shorter / lowe-res video)

- `mcp.md`: Transport STDIO

- Chapter "Orchestration": Add section "Chain" 
  - (simplest "graph" or "workflow")
  - Chain vs workflow (chain -> LangChain)

- `workflows.md`: 
  - Difference between graph and workflow
  - Merge with `grap.md`?
  - Why workflows?
  - Constrained (more constrained => more predictable)
  - More "intelligence" => Less ocnstrained (so advanced agents tend to be less constrained)

- `a2a_introduction.md`: 
  - "Agent-to-Agent (A2A) communication is a coordination pattern" WRONG (a2a is a protocol!)
  - "The A2A pattern" PROTOCOL
  - "It provides the connective tissue that allows multiple workflows," ... multi-agent
  - "How A2A works in practice": sounds made up...Is this a real protocol?

- `mcp_sandbox.md`: It's garbage, re-write
  - BEST PRACTICE: Egress proxy for security
  - Shell commands / Linux (not only python code)

- ADD: deployment server (services)
  - Caddie + ??? (dynamic allocation)
  - BEST PRACTICE: Service state / logs functions

- `repl.md`: 
  - Intro: Mathematica, Jupyter notebooks

- `nl2sql.md`:
  - Postgres: Validate query by asking for the query plan
  - TIP: If the database is a mess, no AI will be able to use it (bad design => useless). Normalization, indexing, etc is necesary
  - BEST PRACTICE: On behalf of user (not super user)

- `autonomous_vs_supervised.md`: Not reviewed!
- Citations: Use autho+number?

- `document_retrieval.md`: 
  - "Candidate Gneeration": "This stage commonly uses either sparse retrieval (e.g., inverted indexes with BM25)...." <= NO! We use a vector database for this!
  - "Scoring": BM25 score. Why? explain what BM25 is
  - Vector database: Postgres `pg_vect` module (previously vector db services...)

- `evaluating_rag.md`:
  - Appendix: Explaine scores BLUE, ROUGE, Recall@k, MRR, nDCG
  - 
- Chapter "Code execution": Move NL2SQL somewhere else (Data chapter)

- IMPLEMENT: Fact checker (run for each chapter)

- IMPLEMENT: Critique

- CONCEPT "Connectors": https://claude.com/connectors

- CONCEPT "Harness": https://www.philschmid.de/agent-harness-2026

- STANDARD "llms.txt": https://llmstxt.org

- BEST PRACTICE: http://www.incompleteideas.net/IncIdeas/BitterLesson.html
- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/writing-tools-for-agents

- https://www.anthropic.com/engineering/multi-agent-research-system

- https://opencode.ai/

- Claude Healthcare: https://www.anthropic.com/news/healthcare-life-sciences
  - Connectors:
    - Centers for Medicare & Medicaid Services (CMS) Coverage Database
    - The International Classification of Diseases, 10th Revision (ICD-10).
    - The National Provider Identifier Registry
    - PubMed
    - FHIR development and a sample prior authorization review skill.
    - HealthEx and Function connectors are available in beta today, while Apple Health and Android Health Connect 
    - Medidata, a leading provider of clinical trial solutions to the life sciences industry
    - ClinicalTrials.gov
    - ToolUniverse
    - bioRxiv & medRxiv
    - Open Targets
    - Owkin, whose Pathology Explorer agent analyzes
    - Connectors: Benchling, 10x Genomics, PubMed, BioRender, Synapse.org, and Wiley Scholar Gateway. 
    - Agent Skills for 
      - scientific problem selection, 
      - converting instrument data to Allotrope
      - Supporting bioinformatics ...for scVI-tools and Nextflow deployment. 
      - Clinical trial protocol draft generation.

- Connectors specification

- Historical perspective: Join at the begiining of the chapter

- Add charts and diagrams (from papers if ArXiv)

- STANDARD UCP (Universal Commerce Protocol): 
  - https://ucp.dev/
  - https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/
  - https://developers.google.com/merchant/ucp

- [A2UI](https://github.com/google/A2UI)

- Prompts: System, prompt, instructions

- Prompt doctor

- BEST PRACTICE (single agent): Define (agent) params in '.env' (use standard variable names across projects): `get_agent()`
- BEST PRACTICE (mult-agent): Define (agent) params in '.agents.json': `get_agent()`
- BEST PRACTICE: Do not hard-code prompts (load prompts from files)
- BEST PRACTICE: Read the prompt! Assume you are a junior person, on their first day at a new job: If you cannot do the task with ONLY the information in the prompt, the agent won't be able to do it either.
- BEST PRACTICE: Doctors / reviewer
  - Prompt Doctor
  - MCP Doctor
  - A2A doctor
  - Skills doctor
  - llms.txt doctor



# Suggested topics

- [Interactions API](https://ai.google.dev/gemini-api/docs/interactions)
- [Claude code VS-Code](https://code.claude.com/docs/en/vs-code)
- [Introducing advanced tool use on the Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use)
- [Personalized AI](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main)
