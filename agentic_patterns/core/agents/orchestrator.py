"""OrchestratorAgent: Full agent with tools, MCP, A2A, skills, sub-agents, and tasks."""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Sequence

import rich
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, RunContext
from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode
from pydantic_ai.agent import AgentRun, AgentRunResult
from pydantic_ai.messages import ModelMessage, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models import Model
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.usage import RunUsage, UsageLimits

from agentic_patterns.core.a2a.client import A2AClientExtended, get_a2a_client
from agentic_patterns.core.a2a.tool import build_coordinator_prompt, create_a2a_tool
from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.models import get_model
from agentic_patterns.core.mcp import MCPClientConfig, load_mcp_settings
from agentic_patterns.core.skills.models import Skill, SkillMetadata
from agentic_patterns.core.skills.registry import SkillRegistry
from agentic_patterns.core.skills.tools import list_available_skills
from agentic_patterns.core.tasks.models import EventType
from agentic_patterns.core.tasks.state import TERMINAL_STATES, TaskState
from agentic_patterns.core.tasks.store import TaskStoreMemory

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


class AgentSpec(BaseModel):
    """Specification for an orchestrator agent with all components resolved."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    model: Model | None = None
    system_prompt: str | None = None
    system_prompt_path: Path | None = None
    tools: list[Any] = []  # Tool | Callable - Pydantic can't validate these types
    mcp_servers: list[MCPClientConfig] = []
    a2a_clients: list[A2AClientExtended] = []
    skills: list[Skill] = []
    sub_agents: list["AgentSpec"] = []

    @classmethod
    def from_config(
        cls,
        name: str,
        *,
        model_name: str = "default",
        system_prompt: str | None = None,
        tool_names: list[str] | None = None,
        mcp_server_names: list[str] | None = None,
        a2a_client_names: list[str] | None = None,
        skill_names: list[str] | None = None,
        skill_roots: list[Path] | None = None,
        config_path: Path | None = None,
    ) -> "AgentSpec":
        """Load and resolve all components from config.yaml."""
        model = get_model(model_name, config_path)

        tools: list[Any] = []
        if tool_names:
            tools = [_resolve_tool(t) for t in tool_names]

        mcp_servers: list[MCPClientConfig] = []
        if mcp_server_names:
            settings = load_mcp_settings(config_path)
            for mcp_name in mcp_server_names:
                config = settings.get(mcp_name)
                if isinstance(config, MCPClientConfig):
                    mcp_servers.append(config)

        a2a_clients: list[A2AClientExtended] = []
        if a2a_client_names:
            a2a_clients = [get_a2a_client(n) for n in a2a_client_names]

        skills: list[Skill] = []
        if skill_roots:
            registry = SkillRegistry()
            registry.discover(skill_roots)
            if skill_names:
                for skill_name in skill_names:
                    skill = registry.get(skill_name)
                    if skill:
                        skills.append(skill)
            else:
                for meta in registry.list_all():
                    skill = registry.get(meta.name)
                    if skill:
                        skills.append(skill)

        return cls(
            name=name,
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            mcp_servers=mcp_servers,
            a2a_clients=a2a_clients,
            skills=skills,
        )

    def __str__(self) -> str:
        counts = []
        if self.tools:
            counts.append(f"tools={len(self.tools)}")
        if self.sub_agents:
            counts.append(f"sub_agents={len(self.sub_agents)}")
        if self.skills:
            counts.append(f"skills={len(self.skills)}")
        if self.mcp_servers:
            counts.append(f"mcp={len(self.mcp_servers)}")
        if self.a2a_clients:
            counts.append(f"a2a={len(self.a2a_clients)}")
        detail = ", ".join(counts)
        return (
            f"AgentSpec({self.name}, {detail})" if detail else f"AgentSpec({self.name})"
        )


class OrchestratorAgent:
    """Composes and runs a PydanticAI agent from an AgentSpec.

    Takes a declarative AgentSpec and wires up all six capabilities: tools, MCP
    servers, A2A clients, skills, sub-agents, and tasks. Used as an async context
    manager: __aenter__ connects MCP servers, fetches A2A agent cards, discovers
    skills, creates the task broker, builds the system prompt from templates and
    catalogs, and instantiates the underlying PydanticAI Agent. __aexit__ cancels
    running tasks and tears down connections.

    The run() method executes a single turn. Message history accumulates across
    calls, enabling multi-turn conversations. Between turns, completed background
    tasks are automatically injected into the prompt.

    Sub-agents and tasks share the same TaskBroker. When sub_agents are present,
    the broker is created and three tools are added: delegate (submit + wait for
    one task), submit_task (fire-and-forget), and wait (event-driven block until
    background work completes). The system prompt controls which tools the agent
    actually uses.

    The context manager is re-entrant: infrastructure is rebuilt on each entry,
    but message history persists across entries.
    """

    def __init__(
        self, spec: AgentSpec, *, verbose: bool = False, on_node: NodeHook | None = None
    ):
        self.spec = spec
        self._on_node = on_node or (_log_node if verbose else None)
        self._agent: Agent | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._system_prompt: str = ""
        self._message_history: list[ModelMessage] = []
        self._runs: list[tuple[AgentRun, list]] = []
        # Task broker (powers both delegate and submit_task/wait)
        self._broker = None
        self._activity = asyncio.Event()
        self._submitted_task_ids: list[str] = []
        self._reported_task_ids: set[str] = set()

    async def __aenter__(self) -> "OrchestratorAgent":
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        tools: list[Any] = list(self.spec.tools)
        mcp_toolsets = self._create_mcp_toolsets()
        a2a_cards = await self._connect_a2a(tools)
        self._discover_skills()
        self._add_skill_tools(tools)
        await self._add_task_tools(tools)

        self._system_prompt = self._build_system_prompt(a2a_cards)
        agent_kwargs: dict[str, Any] = {}
        if mcp_toolsets:
            agent_kwargs["toolsets"] = mcp_toolsets
        self._agent = await asyncio.to_thread(
            get_agent, model=self.spec.model, system_prompt=self._system_prompt, tools=tools, **agent_kwargs
        )
        if mcp_toolsets:
            await self._exit_stack.enter_async_context(self._agent)
        return self

    def _create_mcp_toolsets(self) -> list[MCPServerStreamableHTTP]:
        """Create MCP server toolset objects to pass to the PydanticAI Agent."""
        toolsets = []
        for mcp_config in self.spec.mcp_servers:
            toolsets.append(MCPServerStreamableHTTP(url=mcp_config.url, timeout=mcp_config.read_timeout))
        return toolsets

    async def _connect_a2a(self, tools: list[Any]) -> list[dict]:
        """Fetch A2A agent cards and create delegation tools. Returns A2A cards."""
        a2a_cards: list[dict] = []
        for client in self.spec.a2a_clients:
            card = await client.get_agent_card()
            a2a_cards.append(card)
            tools.append(create_a2a_tool(client, card))
        return a2a_cards

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

    def _add_skill_tools(self, tools: list[Any]) -> None:
        """Add activate_skill tool when skills are present."""
        if not self.spec.skills:
            return
        from agentic_patterns.core.skills.tools import get_all_tools as get_skill_tools

        tools.extend(get_skill_tools(self._make_skill_registry()))

    def _make_skill_registry(self) -> SkillRegistry:
        """Create a SkillRegistry populated with current spec's skills."""
        registry = SkillRegistry()
        registry._metadata_cache = [
            SkillMetadata(name=s.name, description=s.description, path=s.path)
            for s in self.spec.skills
        ]
        return registry

    async def _add_task_tools(self, tools: list[Any]) -> None:
        """Create broker and add sub-agent (delegate) and task (submit_task, wait) tools."""
        if not self.spec.sub_agents:
            return

        sub_map = {s.name: s for s in self.spec.sub_agents}
        names = list(sub_map.keys())

        from agentic_patterns.core.tasks.broker import TaskBroker

        self._broker = TaskBroker(store=TaskStoreMemory(), poll_interval=0.3, activity=self._activity)
        self._broker.register_agents(sub_map)
        await self._exit_stack.enter_async_context(self._broker)

        broker = self._broker
        submitted = self._submitted_task_ids

        tools.append(self._make_delegate_tool(broker, submitted, sub_map, names))
        tools.append(self._make_submit_task_tool(broker, submitted, sub_map, names))
        tools.append(self._make_wait_tool(broker, submitted))

    @staticmethod
    def _make_delegate_tool(
        broker: Any, submitted: list[str], sub_map: dict[str, "AgentSpec"], names: list[str]
    ) -> Any:
        async def delegate(ctx: RunContext, agent_name: str, prompt: str) -> str:
            """Delegate a task to a sub-agent and wait for the result."""
            if agent_name not in sub_map:
                return f"Unknown agent '{agent_name}'. Available: {', '.join(names)}"
            task_id = await broker.submit(prompt, agent_name=agent_name)
            submitted.append(task_id)
            task = await broker.wait(task_id)
            if task is None:
                return "Delegation failed: task not found"
            if task.state == TaskState.COMPLETED:
                for event in reversed(task.events):
                    if event.payload.get("state") == TaskState.COMPLETED.value and "usage" in event.payload:
                        u = event.payload["usage"]
                        ctx.usage.incr(RunUsage(requests=u.get("requests", 0), input_tokens=u.get("input_tokens", 0), output_tokens=u.get("output_tokens", 0)))
                        break
                return task.result or ""
            return f"Delegation failed: {task.error or task.state.value}"

        delegate.__doc__ = f"Delegate a task to a sub-agent and wait for the result. Available agents: {', '.join(names)}."
        return delegate

    @staticmethod
    def _make_submit_task_tool(
        broker: Any, submitted: list[str], sub_map: dict[str, "AgentSpec"], names: list[str]
    ) -> Any:
        async def submit_task(ctx: RunContext, agent_name: str, prompt: str) -> str:
            """Submit a task to a sub-agent for background execution. Returns task_id."""
            if agent_name not in sub_map:
                return f"Unknown agent '{agent_name}'. Available: {', '.join(names)}"
            task_id = await broker.submit(prompt, agent_name=agent_name)
            submitted.append(task_id)
            return f"Task submitted: {task_id[:8]}"

        submit_task.__doc__ = f"Submit a task to a sub-agent for background execution. Returns task_id. Available agents: {', '.join(names)}."
        return submit_task

    def _make_wait_tool(self, broker: Any, submitted: list[str]) -> Any:
        activity = self._activity
        DEFAULT_TIMEOUT = 120

        async def wait(ctx: RunContext, timeout: int = DEFAULT_TIMEOUT) -> str:
            """Wait for background tasks to complete. Blocks until at least one finishes or timeout fires. Returns status and results for all submitted tasks."""
            if not submitted:
                return "No tasks submitted."

            # Clear-then-check pattern: safe against races because the store
            # is updated before the event is set.
            activity.clear()

            # Collect current state -- anything already terminal is returned immediately.
            lines, all_terminal = await _collect_status(broker, submitted)
            if all_terminal:
                return "\n".join(lines)

            # Check if any newly terminal tasks appeared since last call.
            newly_terminal = any(
                line for line in lines if "completed" in line or "failed" in line or "cancelled" in line
            )
            if newly_terminal:
                return "\n".join(lines)

            # Block until signaled or timeout.
            try:
                await asyncio.wait_for(activity.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass

            lines, _ = await _collect_status(broker, submitted)
            return "\n".join(lines)

        return wait

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cancel all running tasks before tearing down
        if self._broker:
            await self._broker.cancel_all()
        if self._exit_stack:
            await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
        self._agent = None
        self._broker = None

    @property
    def system_prompt(self) -> str:
        """Final system prompt built from template, sub-agent catalog, skill catalog, and A2A cards."""
        return self._system_prompt

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

        # Inject completed background tasks into the prompt
        prompt = await self._inject_completed_tasks(prompt)

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

    async def _inject_completed_tasks(self, prompt: str) -> str:
        """Prepend info about background tasks completed since last check."""
        if not self._broker or not self._submitted_task_ids:
            return prompt

        injections = []
        for tid in self._submitted_task_ids:
            if tid in self._reported_task_ids:
                continue
            task = await self._broker.poll(tid)
            if task is None or task.state not in TERMINAL_STATES:
                continue
            self._reported_task_ids.add(tid)
            agent_name = task.metadata.get("agent_name", "unknown")
            if task.state == TaskState.COMPLETED and task.result:
                injections.append(
                    f"[BACKGROUND TASK COMPLETED: {agent_name} (task_id={tid[:8]})]\n"
                    f"Result: {task.result}"
                )
            elif task.state == TaskState.FAILED:
                injections.append(
                    f"[BACKGROUND TASK FAILED: {agent_name} (task_id={tid[:8]})]\n"
                    f"Error: {task.error or 'unknown'}"
                )

        if not injections:
            return prompt

        header = "\n\n".join(injections)
        return f"{header}\n\n{prompt}"

    def _build_system_prompt(self, a2a_cards: list[dict]) -> str:
        """Build combined system prompt from all sources.

        When system_prompt_path is set, loads the template via load_prompt() and
        substitutes {skills_catalog} and {sub_agents_catalog} variables from the
        shared includes. Falls back to the literal system_prompt string otherwise.
        """
        from agentic_patterns.core.prompt import load_prompt

        # Build catalog values for template variables
        variables: dict[str, str] = {}

        if self.spec.sub_agents:
            lines = []
            for sub in self.spec.sub_agents:
                desc = sub.description or sub.name
                lines.append(f"- {sub.name}: {desc}")
            variables["sub_agents_catalog"] = "\n".join(lines)

        if self.spec.skills:
            variables["skills_catalog"] = list_available_skills(self._make_skill_registry())

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

        if a2a_cards:
            prompt = prompt + "\n\n" + build_coordinator_prompt(a2a_cards)

        return prompt

    def __str__(self) -> str:
        return f"OrchestratorAgent({self.spec.name})"


async def _collect_status(broker: Any, submitted: list[str]) -> tuple[list[str], bool]:
    """Return status lines for all submitted tasks and whether all are terminal."""
    lines: list[str] = []
    all_terminal = True
    for tid in submitted:
        task = await broker.poll(tid)
        if task is None:
            lines.append(f"- {tid[:8]}: not found")
            continue
        agent_name = task.metadata.get("agent_name", "unknown")
        status = task.state.value
        line = f"- {tid[:8]} ({agent_name}): {status}"
        if task.state == TaskState.COMPLETED and task.result:
            line += f"\n  Result: {task.result[:200]}"
        elif task.state == TaskState.FAILED and task.error:
            line += f"\n  Error: {task.error}"
        elif task.state not in TERMINAL_STATES:
            all_terminal = False
            progress = [e for e in task.events if e.event_type == EventType.PROGRESS]
            if progress:
                last = progress[-1]
                line += f"\n  Last: {last.payload.get('tool', '')} {last.payload.get('arg', '')}"
        lines.append(line)
    return lines, all_terminal


def _resolve_tool(tool_ref: str) -> Any:
    """Resolve tool reference like 'module.path:function_name' to Tool or Callable."""
    if ":" not in tool_ref:
        raise ValueError(
            f"Invalid tool reference '{tool_ref}'. Expected 'module.path:function_name'"
        )

    module_path, func_name = tool_ref.rsplit(":", 1)

    import importlib

    module = importlib.import_module(module_path)
    func = getattr(module, func_name)

    return func
