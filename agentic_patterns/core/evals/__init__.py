"""Evaluation framework for AI agents.

This module provides infrastructure for discovering, running, and scoring evaluations
using the pydantic-evals framework. It re-exports pydantic_evals classes and adds
agent-specific evaluators and discovery utilities.

Example usage:
    from agentic_patterns.core.evals import Case, Dataset, EqualsExpected, LLMJudge
    from agentic_patterns.core.evals import ToolWasCalled, OutputContainsJson

    dataset = Dataset(
        cases=[Case(name="test", inputs="Hello", expected_output="Hi")],
        evaluators=[EqualsExpected()],
    )
"""

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import (
    Contains,
    EqualsExpected,
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    HasMatchingSpan,
    IsInstance,
    LLMJudge,
    MaxDuration,
)
from pydantic_evals.reporting import EvaluationReport

from agentic_patterns.core.evals.discovery import DiscoveredDataset, discover_datasets, find_eval_files
from agentic_patterns.core.evals.evaluators import NoToolErrors, OutputContainsJson, OutputMatchesSchema, ToolWasCalled
from agentic_patterns.core.evals.runner import PrintOptions, average_assertions, run_all_evaluations, run_evaluation

__all__ = [
    # pydantic_evals re-exports
    "Case",
    "Dataset",
    "Evaluator",
    "EvaluatorContext",
    "EvaluationReason",
    "EvaluationReport",
    "EqualsExpected",
    "Contains",
    "IsInstance",
    "MaxDuration",
    "LLMJudge",
    "HasMatchingSpan",
    # Custom evaluators
    "OutputContainsJson",
    "ToolWasCalled",
    "NoToolErrors",
    "OutputMatchesSchema",
    # Discovery
    "find_eval_files",
    "discover_datasets",
    "DiscoveredDataset",
    # Runner
    "run_evaluation",
    "run_all_evaluations",
    "average_assertions",
    "PrintOptions",
]
