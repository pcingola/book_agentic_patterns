#!/usr/bin/env python3
"""CLI entry point for doctor analysis tools.

Usage:
    python -m agentic_patterns.core.doctors COMMAND [OPTIONS]

Commands:
    tool      Analyze tool functions from a Python module
    prompt    Analyze prompt file(s)
    mcp       Analyze tools from an MCP server
    a2a       Analyze agent-to-agent card(s)

Examples:
    python -m agentic_patterns.core.doctors prompt prompts/system.md
    python -m agentic_patterns.core.doctors tool my_module:my_tools
    python -m agentic_patterns.core.doctors mcp --url http://localhost:8000/mcp
    python -m agentic_patterns.core.doctors mcp --stdio "uv run mcp_server.py"
    python -m agentic_patterns.core.doctors a2a http://localhost:8001/.well-known/agent.json
"""

import argparse
import asyncio
import importlib
import sys
from pathlib import Path

from pydantic_ai.mcp import MCPServerHTTP, MCPServerStdio


def _import_tools(module_spec: str) -> list:
    """Import tools from a module specification like 'module:attr' or 'module'."""
    if ":" in module_spec:
        module_name, attr_name = module_spec.rsplit(":", 1)
    else:
        module_name = module_spec
        attr_name = None

    module = importlib.import_module(module_name)

    if attr_name:
        tools = getattr(module, attr_name)
        if callable(tools):
            return [tools]
        return list(tools)

    # If no attr specified, find all callables that look like tools
    tools = []
    for name in dir(module):
        if name.startswith("_"):
            continue
        obj = getattr(module, name)
        if callable(obj) and hasattr(obj, "__doc__"):
            tools.append(obj)
    return tools


async def cmd_tool(args: argparse.Namespace) -> int:
    """Run tool doctor."""
    from agentic_patterns.core.doctors.tool_doctor import tool_doctor

    tools = _import_tools(args.module)
    if not tools:
        print(f"No tools found in {args.module}")
        return 1

    if args.verbose:
        print(f"Analyzing {len(tools)} tools from {args.module}")

    results = await tool_doctor(tools, batch_size=args.batch_size, verbose=args.verbose)

    for result in results:
        print(result)
        print()

    needs_improvement = sum(1 for r in results if r.needs_improvement)
    print(f"Summary: {needs_improvement}/{len(results)} tools need improvement")
    return 1 if needs_improvement > 0 else 0


async def cmd_prompt(args: argparse.Namespace) -> int:
    """Run prompt doctor."""
    from agentic_patterns.core.doctors.prompt_doctor import prompt_doctor

    paths = [Path(p) for p in args.files]
    for path in paths:
        if not path.exists():
            print(f"File not found: {path}")
            return 1

    if args.verbose:
        print(f"Analyzing {len(paths)} prompts")

    results = await prompt_doctor(paths, batch_size=args.batch_size, verbose=args.verbose)

    for result in results:
        print(result)
        print()

    needs_improvement = sum(1 for r in results if r.needs_improvement)
    print(f"Summary: {needs_improvement}/{len(results)} prompts need improvement")
    return 1 if needs_improvement > 0 else 0


async def cmd_mcp(args: argparse.Namespace) -> int:
    """Run MCP doctor."""
    from agentic_patterns.core.doctors.mcp_doctor import mcp_doctor

    if args.stdio:
        parts = args.stdio.split()
        server = MCPServerStdio(command=parts[0], args=parts[1:])
    else:
        server = MCPServerHTTP(url=args.url)

    if args.verbose:
        print(f"Connecting to MCP server: {args.url or args.stdio}")

    results = await mcp_doctor(server, verbose=args.verbose)

    for result in results:
        print(result)
        print()

    needs_improvement = sum(1 for r in results if r.needs_improvement)
    print(f"Summary: {needs_improvement}/{len(results)} tools need improvement")
    return 1 if needs_improvement > 0 else 0


async def cmd_a2a(args: argparse.Namespace) -> int:
    """Run A2A doctor."""
    from agentic_patterns.core.doctors.a2a_doctor import a2a_doctor

    if args.verbose:
        print(f"Analyzing {len(args.urls)} agent cards")

    results = await a2a_doctor(args.urls, batch_size=args.batch_size, verbose=args.verbose)

    for result in results:
        print(result)
        print()

    needs_improvement = sum(1 for r in results if r.needs_improvement)
    print(f"Summary: {needs_improvement}/{len(results)} agents need improvement")
    return 1 if needs_improvement > 0 else 0


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Doctor analysis tools for prompts, tools, MCP, and A2A")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Tool subcommand
    tool_parser = subparsers.add_parser("tool", help="Analyze tool functions")
    tool_parser.add_argument("module", help="Module spec like 'mymodule:my_tools' or 'mymodule'")
    tool_parser.add_argument("--batch-size", type=int, default=5, help="Tools per batch")

    # Prompt subcommand
    prompt_parser = subparsers.add_parser("prompt", help="Analyze prompt files")
    prompt_parser.add_argument("files", nargs="+", help="Prompt files to analyze")
    prompt_parser.add_argument("--batch-size", type=int, default=5, help="Prompts per batch")

    # MCP subcommand
    mcp_parser = subparsers.add_parser("mcp", help="Analyze MCP server tools")
    mcp_group = mcp_parser.add_mutually_exclusive_group(required=True)
    mcp_group.add_argument("--url", help="HTTP MCP server URL")
    mcp_group.add_argument("--stdio", help="STDIO command (e.g., 'uv run server.py')")

    # A2A subcommand
    a2a_parser = subparsers.add_parser("a2a", help="Analyze A2A agent cards")
    a2a_parser.add_argument("urls", nargs="+", help="Agent card URLs")
    a2a_parser.add_argument("--batch-size", type=int, default=5, help="Agents per batch")

    args = parser.parse_args()

    match args.command:
        case "tool":
            return await cmd_tool(args)
        case "prompt":
            return await cmd_prompt(args)
        case "mcp":
            return await cmd_mcp(args)
        case "a2a":
            return await cmd_a2a(args)
        case _:
            parser.print_help()
            return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path.cwd()))
    sys.exit(asyncio.run(main()))
