"""OrchestratorAgent: Full agent with tools, MCP, A2A, skills, sub-agents, and tasks."""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Any, Sequence

import rich
from pydantic_ai import Agent
from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode
from pydantic_ai.agent import AgentRun, AgentRunResult
from pydantic_ai.messages import ModelMessage, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.usage import UsageLimits

from agentic_patterns.core.a2a.client import A2AClientExtended
from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.orchestrator.agent_spec import AgentSpec
from agentic_patterns.core.agents.orchestrator.status import AgentStatus
from agentic_patterns.core.skills.models import SkillMetadata
from agentic_patterns.core.skills.registry import SkillRegistry

NodeHook = Callable[[Any], None]


def _log_node(node) -> None:
    """Default node hook: print model reasoning, tool calls, and tool results."""
    if isinstance(node, CallToolsNode):
        for part in node.model_response.parts:
            if isinstance(part, TextPart) and part.content.strip():
                line = part.content.strip().replace("\n", " ")[:120]
                rich.print(f"  [dim]> {line}[/dim]")
            elif isinstance(part, ToolCallPart):
                args = part.args_as_dict() or {}
                params = " ".join(f"{k}={v}" for k, v in args.items())
                rich.print(f"  [green]{part.tool_name}[/green] {params[:100]}")
    elif isinstance(node, ModelRequestNode):
        for part in node.request.parts:
            if isinstance(part, ToolReturnPart):
                content = str(part.content).replace("\n", " ")[:120]
                rich.print(f"  [dim]  <- {part.tool_name}: {content}[/dim]")


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
        on_node: NodeHook | None = None,
        task_list: Any | None = None,
    ):
        self.spec = spec
        self._on_node = on_node or (_log_node if verbose else None)
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

        nodes = []
        async with self._agent.iter(
            prompt, usage_limits=usage_limits, message_history=history
        ) as agent_run:
            async for node in agent_run:
                nodes.append(node)
                if self._on_node:
                    self._on_node(node)

        self._runs.append((agent_run, nodes))
        self._message_history.extend(nodes_to_message_history(nodes))
        return agent_run.result

    # -- Private helpers --

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
        """Build combined system prompt from all sources."""
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
            prompt = "\n\n".join(variables.values())

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
