"""OrchestratorAgent: Full agent with tools, MCP, A2A, and skills."""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Sequence

import rich
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, RunContext
from pydantic_ai._agent_graph import CallToolsNode
from pydantic_ai.agent import AgentRun, AgentRunResult
from pydantic_ai.messages import ModelMessage, TextPart, ToolCallPart
from pydantic_ai.models import Model
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.usage import UsageLimits

from agentic_patterns.core.a2a.client import A2AClientExtended, get_a2a_client
from agentic_patterns.core.a2a.tool import build_coordinator_prompt, create_a2a_tool
from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.models import get_model
from agentic_patterns.core.mcp import MCPClientConfig, load_mcp_settings
from agentic_patterns.core.skills.models import Skill, SkillMetadata
from agentic_patterns.core.skills.registry import SkillRegistry
from agentic_patterns.core.skills.tools import list_available_skills

NodeHook = Callable[[Any], None]


def _log_node(node) -> None:
    """Default node hook: print model reasoning and tool calls."""
    if not isinstance(node, CallToolsNode):
        return
    for part in node.model_response.parts:
        if isinstance(part, TextPart) and part.content.strip():
            line = part.content.strip().replace("\n", " ")[:120]
            rich.print(f"  [dim]> {line}[/dim]")
        elif isinstance(part, ToolCallPart):
            args = part.args_as_dict() or {}
            first_val = str(next(iter(args.values()), ""))[:80]
            rich.print(f"  [green]{part.tool_name}[/green] {first_val}")


class AgentSpec(BaseModel):
    """Specification for an orchestrator agent with all components resolved."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    model: Model | None = None
    system_prompt: str | None = None
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
        return f"AgentSpec({self.name}, {detail})" if detail else f"AgentSpec({self.name})"


class OrchestratorAgent:
    """Context manager for running an agent with tools, MCP, A2A, and skills."""

    def __init__(self, spec: AgentSpec, *, verbose: bool = False, on_node: NodeHook | None = None):
        self.spec = spec
        self._on_node = on_node or (_log_node if verbose else None)
        self._agent: Agent | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._mcp_connections: list[Any] = []
        self._message_history: list[ModelMessage] = []
        self._runs: list[tuple[AgentRun, list]] = []

    async def __aenter__(self) -> "OrchestratorAgent":
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        tools: list[Any] = list(self.spec.tools)

        # Create MCP connections
        for mcp_config in self.spec.mcp_servers:
            mcp_client = MCPServerStreamableHTTP(
                url=mcp_config.url, timeout=mcp_config.read_timeout
            )
            connection = await self._exit_stack.enter_async_context(mcp_client)
            self._mcp_connections.append(connection)

        # Create A2A delegation tools
        a2a_cards: list[dict] = []
        for client in self.spec.a2a_clients:
            card = await client.get_agent_card()
            a2a_cards.append(card)
            tool = create_a2a_tool(client, card)
            tools.append(tool)

        # Discover skills from SKILLS_DIR if not provided explicitly
        if not self.spec.skills:
            from agentic_patterns.core.config.config import SKILLS_DIR

            if SKILLS_DIR.exists():
                registry = SkillRegistry()
                registry.discover([SKILLS_DIR])
                self.spec.skills = [
                    s for m in registry.list_all()
                    if (s := registry.get(m.name)) is not None
                ]

        # Create skill tools
        if self.spec.skills:
            from agentic_patterns.core.skills.tools import get_all_tools as get_skill_tools

            registry = SkillRegistry()
            registry._metadata_cache = [
                SkillMetadata(name=s.name, description=s.description, path=s.path)
                for s in self.spec.skills
            ]
            tools.extend(get_skill_tools(registry))

        # Create sub-agent delegation tool
        if self.spec.sub_agents:
            sub_map = {s.name: s for s in self.spec.sub_agents}
            names = list(sub_map.keys())

            async def delegate(ctx: RunContext, agent_name: str, prompt: str) -> str:
                """Delegate a task to a sub-agent."""
                if agent_name not in sub_map:
                    return f"Unknown agent '{agent_name}'. Available: {', '.join(names)}"
                sub_spec = sub_map[agent_name]
                async with OrchestratorAgent(sub_spec) as sub:
                    result = await sub.run(prompt)
                ctx.usage.incr(result.usage())
                return result.output

            delegate.__doc__ = f"Delegate a task to a sub-agent. Available agents: {', '.join(names)}."
            tools.append(delegate)

        # Build system prompt
        system_prompt = self._build_system_prompt(a2a_cards)

        # Create the agent off the event loop -- get_agent() does synchronous
        # file I/O (reads config.yaml) and heavy construction (Agent + instrument).
        self._agent = await asyncio.to_thread(
            get_agent, model=self.spec.model, system_prompt=system_prompt, tools=tools
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._exit_stack:
            await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
        self._mcp_connections = []
        self._agent = None

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

        history = message_history if message_history is not None else (self._message_history or None)

        nodes = []
        async with self._agent.iter(prompt, usage_limits=usage_limits, message_history=history) as agent_run:
            async for node in agent_run:
                nodes.append(node)
                if self._on_node:
                    self._on_node(node)

        self._runs.append((agent_run, nodes))
        self._message_history.extend(nodes_to_message_history(nodes))
        return agent_run.result

    def _build_system_prompt(self, a2a_cards: list[dict]) -> str:
        """Build combined system prompt from all sources."""
        parts: list[str] = []

        if self.spec.system_prompt:
            parts.append(self.spec.system_prompt)

        if a2a_cards:
            parts.append(build_coordinator_prompt(a2a_cards))

        if self.spec.sub_agents:
            lines = ["Available sub-agents (use the `delegate` tool to call them):"]
            for sub in self.spec.sub_agents:
                desc = sub.description or sub.name
                lines.append(f"- {sub.name}: {desc}")
            parts.append("\n".join(lines))

        if self.spec.skills:
            registry = SkillRegistry()
            registry._metadata_cache = [
                SkillMetadata(name=s.name, description=s.description, path=s.path)
                for s in self.spec.skills
            ]
            parts.append("Available skills:\n" + list_available_skills(registry))

        return "\n\n".join(parts) if parts else ""

    def __str__(self) -> str:
        return f"OrchestratorAgent({self.spec.name})"


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
