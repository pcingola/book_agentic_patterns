"""Tool selector that uses an agent to select appropriate tools."""

from typing import Callable

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.tools.utils import func_to_description


SELECTION_PROMPT_TEMPLATE = """Given the user query, select the tools to use.

User query: {query}

Tools available:
{tools_description}

Answer only using the tool names."""


class ToolSelector:
    """Selects relevant tools from a list of functions based on user query."""

    def __init__(self, tools: list[Callable], prompt_template: str | None = None, model=None, config_name: str = "default"):
        self.tools = {func.__name__: func for func in tools}
        self.prompt_template = prompt_template or SELECTION_PROMPT_TEMPLATE
        self.model = model
        self.config_name = config_name

    def _describe_tools(self) -> str:
        return "\n\n".join(func_to_description(func) for func in self.tools.values())

    async def select(self, query: str, verbose: bool = False) -> list[Callable]:
        """Select relevant tools for the given query."""
        agent = get_agent(model=self.model, config_name=self.config_name, output_type=list[str])
        prompt = self.prompt_template.format(query=query, tools_description=self._describe_tools())
        result, _ = await run_agent(agent, prompt, verbose=verbose)
        if result is None:
            return []
        return [self.tools[name] for name in result.result.output if name in self.tools]
