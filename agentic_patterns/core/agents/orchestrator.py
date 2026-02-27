"""OrchestratorAgent: Full agent with tools, MCP, A2A, skills, sub-agents, and tasks."""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Sequence

import rich
import yaml
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent
from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode
from pydantic_ai.agent import AgentRun, AgentRunResult
from pydantic_ai.messages import ModelMessage, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models import Model
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.usage import UsageLimits

from agentic_patterns.core.a2a.client import A2AClientExtended, get_a2a_client
from agentic_patterns.core.agents.agent_status import AgentStatus
from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.models import get_model
from agentic_patterns.core.config.config import MAIN_PROJECT_DIR, PROMPTS_DIR
from agentic_patterns.core.mcp import MCPClientConfig, load_mcp_settings
from agentic_patterns.core.skills.models import Skill, SkillMetadata
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
        model_name: str | None = None,
        system_prompt: str | None = None,
        system_prompt_path: Path | None = None,
        tool_names: list[str] | None = None,
        mcp_server_names: list[str] | None = None,
        a2a_client_names: list[str] | None = None,
        skill_names: list[str] | None = None,
        skill_roots: list[Path] | None = None,
        config_path: Path | None = None,
    ) -> "AgentSpec":
        """Load and resolve all components from config.yaml.

        If an 'agents' section in config.yaml contains an entry for `name`,
        its values are used as defaults. Explicit parameters override YAML values.
        """
        cfg = _load_agent_config(name, config_path)

        model_name = model_name or cfg.get("model", "default")
        model = get_model(model_name, config_path)

        if system_prompt_path is None and "system_prompt" in cfg:
            system_prompt_path = PROMPTS_DIR / cfg["system_prompt"]

        tool_names = tool_names or cfg.get("tools")
        tools: list[Any] = _resolve_tools(tool_names) if tool_names else []

        mcp_server_names = mcp_server_names or cfg.get("mcp_servers")
        mcp_servers: list[MCPClientConfig] = []
        if mcp_server_names:
            settings = load_mcp_settings(config_path)
            for mcp_name in mcp_server_names:
                config = settings.get(mcp_name)
                if isinstance(config, MCPClientConfig):
                    mcp_servers.append(config)

        a2a_client_names = a2a_client_names or cfg.get("a2a_clients")
        a2a_clients: list[A2AClientExtended] = []
        if a2a_client_names:
            a2a_clients = [get_a2a_client(n) for n in a2a_client_names]

        sub_agent_refs = cfg.get("sub_agents", [])
        sub_agents = [_resolve_ref(ref) for ref in sub_agent_refs]

        skill_roots = skill_roots or [Path(p) for p in cfg.get("skill_roots", [])]
        skills: list[Skill] = []
        if skill_roots:
            registry = SkillRegistry()
            registry.discover(skill_roots)
            skill_names = skill_names or cfg.get("skills")
            if skill_names:
                for sn in skill_names:
                    skill = registry.get(sn)
                    if skill:
                        skills.append(skill)
            else:
                for meta in registry.list_all():
                    skill = registry.get(meta.name)
                    if skill:
                        skills.append(skill)

        return cls(
            name=name,
            description=cfg.get("description"),
            model=model,
            system_prompt=system_prompt,
            system_prompt_path=system_prompt_path,
            tools=tools,
            mcp_servers=mcp_servers,
            a2a_clients=a2a_clients,
            skills=skills,
            sub_agents=sub_agents,
        )

    def __str__(self) -> str:
        lines = [f"AgentSpec({self.name})"]
        if self.tools:
            names = [getattr(t, "__name__", type(t).__name__) for t in self.tools]
            lines.append(f"  tools: {', '.join(names)}")
        if self.mcp_servers:
            names = [s.name or s.url for s in self.mcp_servers]
            lines.append(f"  mcp_servers: {', '.join(names)}")
        if self.a2a_clients:
            names = [c._config.name or c._config.url for c in self.a2a_clients]
            lines.append(f"  a2a_clients: {', '.join(names)}")
        if self.sub_agents:
            names = [s.name for s in self.sub_agents]
            lines.append(f"  sub_agents: {', '.join(names)}")
        if self.skills:
            names = [s.name for s in self.skills]
            lines.append(f"  skills: {', '.join(names)}")
        if self.system_prompt_path:
            lines.append(f"  prompt: {self.system_prompt_path.name}")
        return "\n".join(lines)


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

    async def _add_agent_tools(self, tools: list[Any]) -> dict[str, str]:
        """Create AgentRunner and add agent + task tools when agents are present.

        Returns the agents catalog {name: description} for the system prompt.
        """
        has_agents = bool(self.spec.sub_agents or self.spec.a2a_clients)
        if not has_agents:
            return {}

        from agentic_patterns.core.agents.agent_runner import AgentRunner
        from agentic_patterns.core.agents.agent_runner_tools import (
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

    def __str__(self) -> str:
        return f"OrchestratorAgent({self.spec.name})"


def _load_agent_config(name: str, config_path: Path | None = None) -> dict:
    """Load agent config from the 'agents' section of config.yaml. Returns {} if not found."""
    path = config_path or MAIN_PROJECT_DIR / "config.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("agents", {}).get(name, {})


def _resolve_ref(ref: str) -> Any:
    """Resolve 'module.path:callable_name', import it, and call it."""
    if ":" not in ref:
        raise ValueError(
            f"Invalid reference '{ref}'. Expected 'module.path:callable_name'"
        )
    module_path, func_name = ref.rsplit(":", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, func_name)()


def _resolve_tools(refs: list[str]) -> list[Any]:
    """Resolve tool factory references and flatten lists."""
    tools: list[Any] = []
    for ref in refs:
        result = _resolve_ref(ref)
        if isinstance(result, list):
            tools.extend(result)
        else:
            tools.append(result)
    return tools
