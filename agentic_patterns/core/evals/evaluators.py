"""Custom evaluators for agent evaluations.

This module provides Evaluator subclasses for common agent evaluation scenarios
such as JSON validation, tool call verification, and schema validation.
"""

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, EvaluationReason


@dataclass
class OutputContainsJson(Evaluator[Any, Any, Any]):
    """Check if output contains valid JSON."""

    def evaluate(self, ctx: EvaluatorContext[Any, Any, Any]) -> EvaluationReason:
        output = str(ctx.output) if ctx.output is not None else ""
        try:
            json.loads(output)
            return EvaluationReason(value=True, reason="Valid JSON")
        except json.JSONDecodeError as e:
            return EvaluationReason(value=False, reason=f"Invalid JSON: {e}")


@dataclass
class ToolWasCalled(Evaluator[Any, Any, Any]):
    """Check if a specific tool was called during agent execution."""

    tool_name: str

    def evaluate(self, ctx: EvaluatorContext[Any, Any, Any]) -> EvaluationReason:
        if ctx.span_tree is None:
            return EvaluationReason(value=False, reason="No span tree available")
        found = self._find_tool_call(ctx.span_tree, self.tool_name)
        if found:
            return EvaluationReason(value=True, reason=f"Tool '{self.tool_name}' was called")
        return EvaluationReason(value=False, reason=f"Tool '{self.tool_name}' was not called")

    def _find_tool_call(self, span: Any, tool_name: str) -> bool:
        """Recursively search span tree for tool call."""
        if hasattr(span, "name") and tool_name in span.name:
            return True
        if hasattr(span, "children"):
            for child in span.children:
                if self._find_tool_call(child, tool_name):
                    return True
        return False


@dataclass
class NoToolErrors(Evaluator[Any, Any, Any]):
    """Check that no tool calls resulted in errors."""

    def evaluate(self, ctx: EvaluatorContext[Any, Any, Any]) -> EvaluationReason:
        if ctx.span_tree is None:
            return EvaluationReason(value=True, reason="No span tree available (no tools to check)")
        errors = self._find_tool_errors(ctx.span_tree)
        if errors:
            return EvaluationReason(value=False, reason=f"Tool errors found: {errors}")
        return EvaluationReason(value=True, reason="No tool errors")

    def _find_tool_errors(self, span: Any) -> list[str]:
        """Recursively search span tree for tool errors."""
        errors = []
        if hasattr(span, "status") and span.status == "error":
            errors.append(getattr(span, "name", "unknown"))
        if hasattr(span, "children"):
            for child in span.children:
                errors.extend(self._find_tool_errors(child))
        return errors


@dataclass
class OutputMatchesSchema(Evaluator[Any, Any, Any]):
    """Validate output against a Pydantic model or dict schema."""

    schema: type[BaseModel] | dict

    def evaluate(self, ctx: EvaluatorContext[Any, Any, Any]) -> EvaluationReason:
        output = ctx.output
        if output is None:
            return EvaluationReason(value=False, reason="Output is None")

        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError as e:
                return EvaluationReason(value=False, reason=f"Output is not valid JSON: {e}")

        if isinstance(self.schema, type) and issubclass(self.schema, BaseModel):
            try:
                self.schema.model_validate(output)
                return EvaluationReason(value=True, reason="Output matches schema")
            except Exception as e:
                return EvaluationReason(value=False, reason=f"Schema validation failed: {e}")
        elif isinstance(self.schema, dict):
            if not isinstance(output, dict):
                return EvaluationReason(value=False, reason="Output is not a dict")
            missing_keys = set(self.schema.keys()) - set(output.keys())
            if missing_keys:
                return EvaluationReason(value=False, reason=f"Missing keys: {missing_keys}")
            return EvaluationReason(value=True, reason="Output matches schema keys")
        return EvaluationReason(value=False, reason="Invalid schema type")
