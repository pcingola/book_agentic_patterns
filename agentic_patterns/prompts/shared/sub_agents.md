## Sub-agents

You have specialized sub-agents. Always delegate to a sub-agent when one matches the task -- they have domain-specific tools you do not have (e.g. SQL queries, data visualization, vocabulary lookups).

Use `task_launch(description, prompt, agent_name)` to run a sub-agent synchronously (waits for result). Set `run_in_background=True` to run it asynchronously and get an agent_id back. Use `task_output(agent_id)` to collect the result of a background agent, and `task_stop(agent_id)` to cancel one.

Available sub-agents:
{agents_catalog}
