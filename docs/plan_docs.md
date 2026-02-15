# Documentation

We've created the documentation in docs/agnetic_patterns.md (and subdir docs/agnetic_patterns/)

We are going to check the code and make sure all code (except examples) is properly documented.
Goal: An engineer using our library should be able to quickly find the documentation

We'll do this one module at a time, chunking this work into reasonable chunks of works we can handle:

- [x] core/config/ -- 3 files (config.py, env.py, utils.py)
- [x] core/agents/ -- 5 files (agents.py, config.py, models.py, orchestrator.py, utils.py)
- [x] core/connectors/sql/ -- 18 files (connection, connector, operations, inspection, annotation, models, factories, etc.)
- [x] core/connectors/openapi/ -- 13 files (connector, extraction, annotation, client, models, factories, etc.)
- [x] core/connectors/vocabulary/ -- 12 files (connector, strategies, parsers, models, registry, loader, etc.)
- [ ] core/connectors/ (top-level) -- 4 files (base.py, csv.py, file.py, json.py)
- [ ] core/context/ -- 6 files + 9 processor files (decorators, history, reader, models, processors/*)
- [ ] core/mcp/ -- 5 files (config.py, errors.py, factories.py, middleware.py, servers.py)
- [ ] core/a2a/ -- 7 files (client.py, config.py, coordinator.py, middleware.py, mock.py, tool.py, utils.py)
- [ ] core/tasks/ -- 5 files (broker.py, models.py, state.py, store.py, worker.py)
- [ ] core/skills/ -- 3 files (models.py, registry.py, tools.py)
- [ ] core/tools/ -- 3 files (permissions.py, selection.py, utils.py)
- [ ] core/repl/ -- 11 files (executor, sandbox, notebook, cell, image, config, enums, etc.)
- [ ] core/sandbox/ -- 5 files (config.py, container_config.py, manager.py, network_mode.py, session.py)
- [ ] core/evals/ -- 3 files (discovery.py, evaluators.py, runner.py)
- [ ] core/doctors/ -- 6 files (base.py, models.py, prompt/tool/mcp/a2a/skill doctors)
- [ ] core/vectordb/ -- 3 files (config.py, embeddings.py, vectordb.py)
- [ ] core/ui/ -- 5 files (auth.py, cli.py, agui/app.py, agui/events.py, chainlit/*)
- [ ] core/ (standalone) -- 6 files (auth.py, prompt.py, user_session.py, workspace.py, process_sandbox.py, utils.py)
- [ ] core/compliance/ -- 1 file (private_data.py)
- [ ] core/feedback/ -- 1 file (feedback.py)
- [ ] toolkits/data_analysis/ -- 12 files
- [ ] toolkits/data_viz/ -- 9 files
- [ ] toolkits/format_conversion/ -- 4 files
- [ ] toolkits/todo/ -- 2 files
- [ ] tools/ -- 13 files (PydanticAI tool wrappers)
- [ ] agents/ -- 7 files (coordinator, data_analysis, db_catalog, nl2sql, openapi, sql, vocabulary)
- [ ] mcp/ -- 11 servers (template, todo, sql, data_analysis, data_viz, format_conversion, file_ops, repl, sandbox, vocabulary, openapi)
- [ ] a2a/ -- 5 servers (template, nl2sql, data_analysis, vocabulary, openapi)
- [ ] testing/ -- 3 files (agent_mock.py, model_mock.py, tool_mock.py)

Methodology: 
1. Pick the next (unchecked) module in the list
2. Document the code, ensuring that the important functions, classes, and modules are well-explained and easy to understand for engineers using the library.
3. Once done, mark it as done in the checklist.
4. Move to the next module. When your context windows is (estimated) at 60% or more, stop and wait for me to review before proceeding with the next items.
