# To do

REPL:
- [ ] Dirs are wrong: /workspace/.repl and /workspace/mcp_repl/cells.json
- [ ] Add a new tool "create jupyter notebook" so that the agent can create a notebook the users can download and open in VS-Code
- [ ] If neither bwrap nor docker is available => Exception with clear message. NO silently fall back to a dangerous non-sandboxed execution. Same for sandbox!
- [ ] Cell errors should NOT print the full stack trace going through internal REPL code. Instead, it should print a clear error message with the cell content and the error message. The stack trace should be cut when we hit the REPL code. This is to avoid overwhelming the user with internal details and to focus on the relevant error information.

Implement each item, updte documentation, then mark it as done before going on to the next item in the list





### References and Suggested topics

- Claude Engineering blog: See resource from https://www.anthropic.com/engineering
- "Harness": https://www.philschmid.de/agent-harness-2026
- STANDARD "llms.txt": https://llmstxt.org
- BEST PRACTICE: http://www.incompleteideas.net/IncIdeas/BitterLesson.html
- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://www.anthropic.com/engineering/multi-agent-research-system
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

- [Interactions API](https://ai.google.dev/gemini-api/docs/interactions)
- [Introducing advanced tool use on the Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use)
- [Personalized AI](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main)
- [Genetic Algorithms for search](https://arxiv.org/html/2601.10657v1)

