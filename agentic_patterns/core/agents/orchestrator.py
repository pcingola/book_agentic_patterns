"""OrchestratorAgent: Full agent with tools, MCP, A2A, and skills."""

from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRun
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.usage import UsageLimits

from agentic_patterns.core.a2a.client import A2AClientExtended, get_a2a_client
from agentic_patterns.core.a2a.tool import build_coordinator_prompt, create_a2a_tool
from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.agents.models import get_model
from agentic_patterns.core.mcp import MCPClientConfig, load_mcp_settings
from agentic_patterns.core.skills.models import Skill, SkillMetadata
from agentic_patterns.core.skills.registry import SkillRegistry
from agentic_patterns.core.skills.tools import list_available_skills


class AgentSpec(BaseModel):
    """Specification for an orchestrator agent with all components resolved."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    model: Model
    system_prompt: str | None = None
    tools: list[Any] = []  # Tool | Callable - Pydantic can't validate these types
    mcp_servers: list[MCPClientConfig] = []
    a2a_clients: list[A2AClientExtended] = []
    skills: list[Skill] = []

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
        if skill_names and skill_roots:
            registry = SkillRegistry()
            registry.discover(skill_roots)
            for skill_name in skill_names:
                skill = registry.get(skill_name)
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
        return f"AgentSpec({self.name})"


class OrchestratorAgent:
    """Context manager for running an agent with tools, MCP, A2A, and skills."""

    def __init__(self, spec: AgentSpec):
        self.spec = spec
        self._agent: Agent | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._mcp_connections: list[Any] = []

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

        # Build system prompt
        system_prompt = self._build_system_prompt(a2a_cards)

        # Create the agent
        self._agent = get_agent(
            model=self.spec.model,
            system_prompt=system_prompt,
            tools=tools,
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._exit_stack:
            await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
        self._mcp_connections = []
        self._agent = None

    async def run(
        self,
        prompt: str,
        *,
        message_history: Sequence[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
        verbose: bool = False,
    ) -> tuple[AgentRun | None, list[ModelMessage]]:
        """Run the agent with the given prompt."""
        if not self._agent:
            raise RuntimeError(
                "OrchestratorAgent must be used as async context manager"
            )

        return await run_agent(
            self._agent,
            prompt,
            message_history=message_history,
            usage_limits=usage_limits,
            verbose=verbose,
        )

    def _build_system_prompt(self, a2a_cards: list[dict]) -> str:
        """Build combined system prompt from all sources."""
        parts: list[str] = []

        if self.spec.system_prompt:
            parts.append(self.spec.system_prompt)

        if a2a_cards:
            parts.append(build_coordinator_prompt(a2a_cards))

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
