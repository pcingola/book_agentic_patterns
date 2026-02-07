# Pydantic AI Documentation

Split from `pydantic-ai.llms-full.txt` (original in `docs/original/`).

## Getting Started

- [Pydantic AI](pydantic-ai/01_pydantic_ai.md)
- [Pydantic AI](pydantic-ai/03_pydantic_ai.md)
- [Installation](pydantic-ai/04_installation.md)
- [Getting Help](pydantic-ai/05_getting_help.md)
- [Troubleshooting](pydantic-ai/06_troubleshooting.md)

## Concepts

- [Agent2Agent (A2A) Protocol](pydantic-ai/08_agent2agent_a2a_protocol.md)
- [Built-in Tools](pydantic-ai/09_built_in_tools.md)
- [Dependencies](pydantic-ai/10_dependencies.md)
- [Deferred Tools](pydantic-ai/11_deferred_tools.md)
- [Direct Model Requests](pydantic-ai/12_direct_model_requests.md)
- [Embeddings](pydantic-ai/13_embeddings.md)
- [Image, Audio, Video & Document Input](pydantic-ai/14_image_audio_video_document_input.md)
- [Function Tools](pydantic-ai/15_function_tools.md)
- [Common Tools](pydantic-ai/16_common_tools.md)
- [HTTP Request Retries](pydantic-ai/17_http_request_retries.md)
- [Messages and chat history](pydantic-ai/18_messages_and_chat_history.md)
- [Multi-agent Applications](pydantic-ai/19_multi_agent_applications.md)
- [Thinking](pydantic-ai/20_thinking.md)
- [Third-Party Tools](pydantic-ai/21_third_party_tools.md)
- [Advanced Tool Features](pydantic-ai/22_advanced_tool_features.md)
- [Toolsets](pydantic-ai/23_toolsets.md)

## Models

- [Anthropic](pydantic-ai/25_anthropic.md)
- [Bedrock](pydantic-ai/26_bedrock.md)
- [Cerebras](pydantic-ai/27_cerebras.md)
- [Cohere](pydantic-ai/28_cohere.md)
- [Google](pydantic-ai/29_google.md)
- [Groq](pydantic-ai/30_groq.md)
- [Hugging Face](pydantic-ai/31_hugging_face.md)
- [Mistral](pydantic-ai/32_mistral.md)
- [OpenAI](pydantic-ai/33_openai.md)
- [OpenRouter](pydantic-ai/34_openrouter.md)
- [Outlines](pydantic-ai/35_outlines.md)
- [Model Providers](pydantic-ai/36_model_providers.md)
- [xAI](pydantic-ai/37_xai.md)

## Graphs

- [Graphs](pydantic-ai/39_graphs.md)

## API Reference

- [`pydantic_ai.ag_ui`](pydantic-ai/41_pydantic_ai_ag_ui.md)
- [`pydantic_ai.agent`](pydantic-ai/42_pydantic_ai_agent.md)
- [`pydantic_ai.builtin_tools`](pydantic-ai/43_pydantic_ai_builtin_tools.md)
- [`pydantic_ai.common_tools`](pydantic-ai/44_pydantic_ai_common_tools.md)
- [`pydantic_ai` -- Concurrency](pydantic-ai/45_pydantic_ai_concurrency.md)
- [`pydantic_ai.direct`](pydantic-ai/46_pydantic_ai_direct.md)
- [`pydantic_ai.durable_exec`](pydantic-ai/47_pydantic_ai_durable_exec.md)
- [`pydantic_ai.embeddings`](pydantic-ai/48_pydantic_ai_embeddings.md)
- [`pydantic_ai.exceptions`](pydantic-ai/49_pydantic_ai_exceptions.md)
- [`pydantic_ai.ext`](pydantic-ai/50_pydantic_ai_ext.md)
- [`fasta2a`](pydantic-ai/51_fasta2a.md)
- [`pydantic_ai.format_prompt`](pydantic-ai/52_pydantic_ai_format_prompt.md)
- [`pydantic_ai.mcp`](pydantic-ai/53_pydantic_ai_mcp.md)
- [`pydantic_ai.messages`](pydantic-ai/54_pydantic_ai_messages.md)
- [`pydantic_ai.output`](pydantic-ai/55_pydantic_ai_output.md)
- [`pydantic_ai.profiles`](pydantic-ai/56_pydantic_ai_profiles.md)
- [`pydantic_ai.providers`](pydantic-ai/57_pydantic_ai_providers.md)
- [`pydantic_ai.result`](pydantic-ai/58_pydantic_ai_result.md)
- [`pydantic_ai.retries`](pydantic-ai/59_pydantic_ai_retries.md)
- [`pydantic_ai.run`](pydantic-ai/60_pydantic_ai_run.md)
- [`pydantic_ai.settings`](pydantic-ai/61_pydantic_ai_settings.md)
- [`pydantic_ai.tools`](pydantic-ai/62_pydantic_ai_tools.md)
- [`pydantic_ai.toolsets`](pydantic-ai/63_pydantic_ai_toolsets.md)
- [`pydantic_ai.usage`](pydantic-ai/64_pydantic_ai_usage.md)

## API Reference -- Models

- [`pydantic_ai.models.anthropic`](pydantic-ai/65_pydantic_ai_models_anthropic.md)
- [`pydantic_ai.models`](pydantic-ai/66_pydantic_ai_models.md)
- [`pydantic_ai.models.bedrock`](pydantic-ai/67_pydantic_ai_models_bedrock.md)
- [`pydantic_ai.models.cerebras`](pydantic-ai/68_pydantic_ai_models_cerebras.md)
- [`pydantic_ai.models.cohere`](pydantic-ai/69_pydantic_ai_models_cohere.md)
- [`pydantic_ai.models.fallback`](pydantic-ai/70_pydantic_ai_models_fallback.md)
- [`pydantic_ai.models.function`](pydantic-ai/71_pydantic_ai_models_function.md)
- [`pydantic_ai.models.google`](pydantic-ai/72_pydantic_ai_models_google.md)
- [`pydantic_ai.models.groq`](pydantic-ai/73_pydantic_ai_models_groq.md)
- [`pydantic_ai.models.huggingface`](pydantic-ai/74_pydantic_ai_models_huggingface.md)
- [`pydantic_ai.models.instrumented`](pydantic-ai/75_pydantic_ai_models_instrumented.md)
- [`pydantic_ai.models.mcp_sampling`](pydantic-ai/76_pydantic_ai_models_mcp_sampling.md)
- [`pydantic_ai.models.mistral`](pydantic-ai/77_pydantic_ai_models_mistral.md)
- [`pydantic_ai.models.openai`](pydantic-ai/78_pydantic_ai_models_openai.md)
- [`pydantic_ai.models.openrouter`](pydantic-ai/79_pydantic_ai_models_openrouter.md)
- [`pydantic_ai.models.outlines`](pydantic-ai/80_pydantic_ai_models_outlines.md)
- [`pydantic_ai.models.test`](pydantic-ai/81_pydantic_ai_models_test.md)
- [`pydantic_ai.models.wrapper`](pydantic-ai/82_pydantic_ai_models_wrapper.md)
- [`pydantic_ai.models.xai`](pydantic-ai/83_pydantic_ai_models_xai.md)

## API Reference -- Evals

- [`pydantic_evals.dataset`](pydantic-ai/84_pydantic_evals_dataset.md)
- [`pydantic_evals.evaluators`](pydantic-ai/85_pydantic_evals_evaluators.md)
- [`pydantic_evals.generation`](pydantic-ai/86_pydantic_evals_generation.md)
- [`pydantic_evals.otel`](pydantic-ai/87_pydantic_evals_otel.md)
- [`pydantic_evals.reporting`](pydantic-ai/88_pydantic_evals_reporting.md)

## API Reference -- Graph

- [`pydantic_graph.beta`](pydantic-ai/89_pydantic_graph_beta.md)
- [`pydantic_graph.beta.decision`](pydantic-ai/90_pydantic_graph_beta_decision.md)
- [`pydantic_graph.beta.graph`](pydantic-ai/91_pydantic_graph_beta_graph.md)
- [`pydantic_graph.beta.graph_builder`](pydantic-ai/92_pydantic_graph_beta_graph_builder.md)
- [`pydantic_graph.beta.join`](pydantic-ai/93_pydantic_graph_beta_join.md)
- [`pydantic_graph.beta.node`](pydantic-ai/94_pydantic_graph_beta_node.md)
- [`pydantic_graph.beta.step`](pydantic-ai/95_pydantic_graph_beta_step.md)
- [`pydantic_graph.exceptions`](pydantic-ai/96_pydantic_graph_exceptions.md)
- [`pydantic_graph`](pydantic-ai/97_pydantic_graph.md)
- [`pydantic_graph.mermaid`](pydantic-ai/98_pydantic_graph_mermaid.md)
- [`pydantic_graph.nodes`](pydantic-ai/99_pydantic_graph_nodes.md)
- [`pydantic_graph.persistence`](pydantic-ai/100_pydantic_graph_persistence.md)

## API Reference -- UI

- [`pydantic_ai.ui.ag_ui`](pydantic-ai/101_pydantic_ai_ui_ag_ui.md)
- [`pydantic_ai.ui`](pydantic-ai/102_pydantic_ai_ui.md)
- [`pydantic_ai.ui.vercel_ai`](pydantic-ai/103_pydantic_ai_ui_vercel_ai.md)

## Evals

- [Pydantic Evals](pydantic-ai/105_pydantic_evals.md)

## Durable Execution

- [Durable Execution with DBOS](pydantic-ai/107_durable_execution_with_dbos.md)
- [Durable Execution](pydantic-ai/108_durable_execution.md)
- [Durable Execution with Prefect](pydantic-ai/109_durable_execution_with_prefect.md)
- [Durable Execution with Temporal](pydantic-ai/110_durable_execution_with_temporal.md)

## MCP

- [Client](pydantic-ai/112_client.md)
- [FastMCP Client](pydantic-ai/113_fastmcp_client.md)
- [Model Context Protocol (MCP)](pydantic-ai/114_model_context_protocol_mcp.md)
- [Server](pydantic-ai/115_server.md)

## UI Event Streams

- [Agent-User Interaction (AG-UI) Protocol](pydantic-ai/117_agent_user_interaction_ag_ui_protocol.md)
- [UI Event Streams](pydantic-ai/118_ui_event_streams.md)
- [Vercel AI Data Stream Protocol](pydantic-ai/119_vercel_ai_data_stream_protocol.md)

## Optional

- [Unit testing](pydantic-ai/121_unit_testing.md)
- [Command Line Interface (CLI)](pydantic-ai/122_command_line_interface_cli.md)
- [Pydantic Logfire Debugging and Monitoring](pydantic-ai/123_pydantic_logfire_debugging_and_monitoring.md)
- [Upgrade Guide](pydantic-ai/124_upgrade_guide.md)

## Examples

- [Agent User Interaction (AG-UI)](pydantic-ai/126_agent_user_interaction_ag_ui.md)
- [Chat App with FastAPI](pydantic-ai/127_chat_app_with_fastapi.md)
- [Data Analyst](pydantic-ai/128_data_analyst.md)
- [Pydantic Model](pydantic-ai/129_pydantic_model.md)
- [Question Graph](pydantic-ai/130_question_graph.md)
- [RAG](pydantic-ai/131_rag.md)
- [Examples](pydantic-ai/132_examples.md)
- [Slack Lead Qualifier with Modal](pydantic-ai/133_slack_lead_qualifier_with_modal.md)
- [SQL Generation](pydantic-ai/134_sql_generation.md)
