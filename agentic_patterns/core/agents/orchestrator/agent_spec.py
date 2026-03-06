"""AgentSpec: declarative specification for an orchestrator agent."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict
from pydantic_ai.models import Model

from agentic_patterns.core.a2a.client import A2AClientExtended, get_a2a_client
from agentic_patterns.core.agents.models import get_model
from agentic_patterns.core.config.config import MAIN_PROJECT_DIR
from agentic_patterns.core.prompt import load_prompt as _load_prompt
from agentic_patterns.core.mcp import MCPClientConfig, load_mcp_settings
from agentic_patterns.core.skills.models import Skill
from agentic_patterns.core.skills.registry import SkillRegistry


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
    file_tools: bool = False
    sandbox: bool = False
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

        if (
            system_prompt is None
            and system_prompt_path is None
            and "system_prompt" in cfg
        ):
            system_prompt = _load_prompt(cfg["system_prompt"])

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
            file_tools=cfg.get("file_tools", False),
            sandbox=cfg.get("sandbox", False),
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
        if self.file_tools:
            lines.append("  file_tools: enabled")
        if self.sandbox:
            lines.append("  sandbox: enabled")
        if self.system_prompt_path:
            lines.append(f"  prompt: {self.system_prompt_path.name}")
        return "\n".join(lines)


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
