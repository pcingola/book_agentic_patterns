"""OrchestratorAgent: Full agent with tools, MCP, A2A, skills, sub-agents, and tasks."""

import asyncio
from contextlib import AsyncExitStack
from typing import Any, Sequence

from pydantic_ai import Agent
from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode
from pydantic_ai.agent import AgentRun, AgentRunResult
from pydantic_ai.messages import ModelMessage, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.usage import UsageLimits

import rich

from agentic_patterns.core.a2a.client import A2AClientExtended
from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.orchestrator.agent_spec import AgentSpec
from agentic_patterns.core.agents.orchestrator.status import AgentStatus
from agentic_patterns.core.listeners import AgentListener, PrintAgentListener
from agentic_patterns.core.skills.models import SkillMetadata
from agentic_patterns.core.skills.registry import SkillRegistry

_SKILL_TOOLS = {"activate_skill", "run_skill_script"}
_AGENT_TOOLS = {"task_launch", "task_output", "task_stop"}


class OrchestratorAgent:
    """Composes and runs a PydanticAI agent from an AgentSpec.

    Takes a declarative AgentSpec and wires up all capabilities: tools, MCP
    servers, skills, and agents (local sub-agents and remote A2A agents via
    unified AgentRunner) with tasks (via TaskList). Used as an async context
    manager.

    The run() method executes a single turn. Message history accumulates across
    calls, enabling multi-turn conversations. Between turns, completed background
    agents are automatically injected into the prompt.
    """

    def __init__(
        self,
        spec: AgentSpec,
        *,
        verbose: bool = False,
        listener: AgentListener | None = None,
        task_list: Any | None = None,
    ):
        self.spec = spec
        self._verbose = verbose
        self._listener = listener
        self._agent: Agent | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._system_prompt: str = ""
        self._message_history: list[ModelMessage] = []
        self._runs: list[tuple[AgentRun, list]] = []
        self._agent_runner = None
        self._task_list = task_list  # None = create new; provided = shared from parent
        self._reported_agent_ids: set[str] = set()

    async def __aenter__(self) -> "OrchestratorAgent":
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        tools: list[Any] = list(self.spec.tools)
        if self.spec.file_tools:
            self._add_file_tools(tools)
        if self.spec.sandbox:
            self._add_sandbox_tools(tools)
        mcp_toolsets = self._create_mcp_toolsets()
        self._discover_skills()
        self._add_skill_tools(tools)
        agents_catalog = await self._add_agent_tools(tools)

        self._system_prompt = self._build_system_prompt(agents_catalog)
        agent_kwargs: dict[str, Any] = {}
        if mcp_toolsets:
            agent_kwargs["toolsets"] = mcp_toolsets
        self._agent = await asyncio.to_thread(
            get_agent,
            model=self.spec.model,
            system_prompt=self._system_prompt,
            tools=tools,
            **agent_kwargs,
        )
        if mcp_toolsets:
            await self._exit_stack.enter_async_context(self._agent)

        if self._listener is None and self._verbose:
            self._listener = PrintAgentListener()
        if self._verbose and self._task_list:
            self._task_list.on_change = lambda: rich.print(f"\n{self._task_list}\n")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._agent_runner:
            await self._agent_runner.cancel_all()
        if self._exit_stack:
            await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
        self._agent = None
        self._agent_runner = None

    @property
    def agent_runner(self) -> Any:
        return self._agent_runner

    @property
    def system_prompt(self) -> str:
        """Final system prompt built from template, agent catalog, and skill catalog."""
        return self._system_prompt

    @property
    def task_list(self) -> Any:
        return self._task_list

    @property
    def runs(self) -> list[tuple[AgentRun, list]]:
        """History of all (AgentRun, nodes) from each run() call."""
        return self._runs

    async def run(
        self,
        prompt: str,
        *,
        message_history: Sequence[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> AgentRunResult:
        """Run the agent with the given prompt. Accumulates message history across turns."""
        if not self._agent:
            raise RuntimeError(
                "OrchestratorAgent must be used as async context manager"
            )

        from agentic_patterns.core.agents.utils import nodes_to_message_history

        prompt = await self._inject_completed_agents(prompt)

        history = (
            message_history
            if message_history is not None
            else (self._message_history or None)
        )

        if self._listener:
            await self._listener.on_start()

        nodes = []
        async with self._agent.iter(
            prompt, usage_limits=usage_limits, message_history=history
        ) as agent_run:
            async for node in agent_run:
                nodes.append(node)
                if self._listener:
                    await self._dispatch_node(node)

        self._runs.append((agent_run, nodes))
        self._message_history.extend(nodes_to_message_history(nodes))

        if self._listener:
            await self._listener.on_done(agent_run.result)
        return agent_run.result

    # -- Private helpers --

    async def _dispatch_node(self, node: Any) -> None:
        """Translate a PydanticAI node into AgentListener calls."""
        if isinstance(node, CallToolsNode):
            for part in node.model_response.parts:
                if isinstance(part, TextPart) and part.content.strip():
                    await self._listener.on_text(part.content.strip())
                elif isinstance(part, ToolCallPart):
                    args = part.args_as_dict() or {}
                    if part.tool_name in _SKILL_TOOLS:
                        await self._listener.on_skill_call(
                            args.get("skill_name", part.tool_name)
                        )
                    elif part.tool_name == "task_launch":
                        await self._listener.on_agent_launch(args.get("agent_name", ""))
                    elif part.tool_name not in _AGENT_TOOLS:
                        await self._listener.on_tool_call(part.tool_name, args)
        elif isinstance(node, ModelRequestNode):
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    content = str(part.content)
                    if part.tool_name in {"task_launch", "task_output"}:
                        await self._listener.on_agent_done(content)
                    elif part.tool_name not in _AGENT_TOOLS:
                        await self._listener.on_tool_result(part.tool_name, content)

    async def _add_agent_tools(self, tools: list[Any]) -> dict[str, str]:
        """Create AgentRunner and add agent + task tools when agents are present.

        Returns the agents catalog {name: description} for the system prompt.
        """
        has_agents = bool(self.spec.sub_agents or self.spec.a2a_clients)
        if not has_agents:
            return {}

        from agentic_patterns.core.agents.orchestrator.runner import AgentRunner
        from agentic_patterns.core.agents.orchestrator.runner_tools import (
            get_agent_runner_tools,
        )

        # Build local agents map
        local_agents = {s.name: s for s in self.spec.sub_agents}

        # Build remote agents map: fetch agent cards
        remote_agents: dict[str, tuple[A2AClientExtended, dict]] = {}
        for client in self.spec.a2a_clients:
            card = await client.get_agent_card()
            name = card.get("name", "remote")
            remote_agents[name] = (client, card)

        self._agent_runner = AgentRunner(local_agents, remote_agents)

        # Create or reuse TaskList
        if self._task_list is None:
            import uuid
            from agentic_patterns.core.config.config import WORKSPACE_DIR
            from agentic_patterns.core.tasks import TaskList

            list_id = str(uuid.uuid4())[:8]
            base_dir = WORKSPACE_DIR / ".tasks" / list_id
            self._task_list = TaskList(base_dir)

        # Share TaskList with AgentRunner so child agents inherit it
        self._agent_runner._task_list = self._task_list

        # Add task management tools
        from agentic_patterns.core.tasks import get_task_tools

        tools.extend(get_task_tools(self._task_list))

        # Add agent spawning tools
        tools.extend(get_agent_runner_tools(self._agent_runner))

        return self._agent_runner.catalog()

    def _build_system_prompt(self, agents_catalog: dict[str, str]) -> str:
        """Build combined system prompt from all sources.

        When using a prompt file (system_prompt_path), the file controls what
        shared blocks to include via {% include %}.  When using an inline
        system_prompt, task and agent workflow instructions are appended
        automatically so the agent knows how to use them.
        """
        from agentic_patterns.core.prompt import load_prompt

        variables: dict[str, str] = {}

        if agents_catalog:
            lines = [f"- {name}: {desc}" for name, desc in agents_catalog.items()]
            variables["agents_catalog"] = "\n".join(lines)

        if self.spec.skills:
            variables["skills_catalog"] = self._make_skill_registry().catalog()

        if self.spec.system_prompt_path:
            prompt = load_prompt(self.spec.system_prompt_path, **variables)
        elif self.spec.system_prompt:
            prompt = (
                self.spec.system_prompt.format(**variables)
                if variables
                else self.spec.system_prompt
            )
        else:
            raise ValueError(
                f"AgentSpec '{self.spec.name}' has no system_prompt or system_prompt_path"
            )

        # For inline prompts, auto-append shared prompt blocks based on
        # available capabilities.  Prompt files handle this via {% include %}.
        if not self.spec.system_prompt_path:
            prompt = self._append_shared_blocks(prompt, variables, agents_catalog)

        return prompt

    def _append_shared_blocks(
        self,
        prompt: str,
        variables: dict[str, str],
        agents_catalog: dict[str, str],
    ) -> str:
        """Append shared prompt blocks for capabilities the agent actually has."""
        from agentic_patterns.core.config.config import PROMPTS_DIR
        from agentic_patterns.core.prompt import load_prompt

        shared = PROMPTS_DIR / "shared"
        # (condition, filename, variables needed by that file)
        blocks: list[tuple[bool, str, dict[str, str]]] = [
            (True, "workspace.md", {}),
            (self.spec.file_tools, "file_tools.md", {}),
            (self.spec.sandbox, "sandbox.md", {}),
            (bool(self._task_list), "tasks.md", {}),
            (
                bool(self.spec.skills),
                "skills.md",
                {"skills_catalog": variables.get("skills_catalog", "")},
            ),
            (
                bool(agents_catalog),
                "sub_agents.md",
                {"agents_catalog": variables.get("agents_catalog", "")},
            ),
        ]
        for condition, filename, file_vars in blocks:
            path = shared / filename
            if condition and path.exists():
                prompt += "\n\n" + load_prompt(path, **file_vars)

        return prompt

    def _create_mcp_toolsets(self) -> list[MCPServerStreamableHTTP]:
        """Create MCP server toolset objects to pass to the PydanticAI Agent."""
        toolsets = []
        for mcp_config in self.spec.mcp_servers:
            toolsets.append(
                MCPServerStreamableHTTP(
                    url=mcp_config.url, timeout=mcp_config.read_timeout
                )
            )
        return toolsets

    def _discover_skills(self) -> None:
        """Auto-discover skills from SKILLS_DIR when none are provided explicitly."""
        if self.spec.skills:
            return
        from agentic_patterns.core.config.config import SKILLS_DIR

        if not SKILLS_DIR.exists():
            return
        registry = SkillRegistry()
        registry.discover([SKILLS_DIR])
        self.spec.skills = [
            s for m in registry.list_all() if (s := registry.get(m.name)) is not None
        ]

    async def _inject_completed_agents(self, prompt: str) -> str:
        """Prepend info about background agents completed since last check.

        For local agents the asyncio.Task result is already available.
        For remote agents, makes one get_task call per pending agent.
        """
        if not self._agent_runner:
            return prompt

        # Check remote agents for completion
        for agent_id, result in self._agent_runner._results.items():
            if result.status == AgentStatus.RUNNING and result._remote_task_id:
                await self._agent_runner.check_remote(agent_id)

        injections = []
        for agent_id, result in self._agent_runner._results.items():
            if agent_id in self._reported_agent_ids:
                continue
            if result.status == AgentStatus.RUNNING:
                continue
            self._reported_agent_ids.add(agent_id)
            if result.status == AgentStatus.COMPLETED and result.output:
                injections.append(
                    f"[BACKGROUND AGENT COMPLETED: {result.agent_name} (id={agent_id})]\n"
                    f"Result: {result.output}"
                )
            elif result.status == AgentStatus.FAILED:
                injections.append(
                    f"[BACKGROUND AGENT FAILED: {result.agent_name} (id={agent_id})]\n"
                    f"Error: {result.error or 'unknown'}"
                )

        if not injections:
            return prompt
        header = "\n\n".join(injections)
        return f"{header}\n\n{prompt}"

    def _add_file_tools(self, tools: list[Any]) -> None:
        """Add file, CSV, and JSON tools when file_tools is enabled."""
        from agentic_patterns.tools.file import get_all_tools as get_file_tools
        from agentic_patterns.tools.csv import get_all_tools as get_csv_tools
        from agentic_patterns.tools.json import get_all_tools as get_json_tools

        tools.extend(get_file_tools())
        tools.extend(get_csv_tools())
        tools.extend(get_json_tools())

    def _add_sandbox_tools(self, tools: list[Any]) -> None:
        """Add sandbox_execute tool when sandbox is enabled."""
        from agentic_patterns.tools.sandbox import get_all_tools

        tools.extend(get_all_tools())

    def _add_skill_tools(self, tools: list[Any]) -> None:
        """Add activate_skill and run_skill_script tools when skills are present."""
        if not self.spec.skills:
            return
        from agentic_patterns.core.skills.tools import create_skill_sandbox_manager

        registry = self._make_skill_registry()
        sandbox = create_skill_sandbox_manager(registry)
        tools.extend(registry.get_all_tools(sandbox=sandbox))

    def _make_skill_registry(self) -> SkillRegistry:
        """Create a SkillRegistry populated with current spec's skills."""
        registry = SkillRegistry()
        registry._metadata_cache = [
            SkillMetadata(name=s.name, description=s.description, path=s.path)
            for s in self.spec.skills
        ]
        return registry

    def __str__(self) -> str:
        return f"OrchestratorAgent({self.spec.name})"
