"""Evaluation execution and orchestration.

This module handles running evaluations and determining pass/fail status.
"""

import sys
from dataclasses import dataclass

from pydantic_evals.reporting import EvaluationReport

from agentic_patterns.core.evals.discovery import DiscoveredDataset


@dataclass
class PrintOptions:
    """Options for printing evaluation reports."""

    include_input: bool = True
    include_output: bool = True
    include_evaluator_failures: bool = False
    include_reasons: bool = False


def average_assertions(report: EvaluationReport, min_score: float = 1.0) -> bool:
    """Check if the average assertion score meets a threshold."""
    averages = report.averages()
    if averages and averages.assertions is not None:
        return averages.assertions >= min_score
    return False


async def run_evaluation(discovered: DiscoveredDataset, print_options: PrintOptions, min_assertions: float = 1.0, verbose: bool = False) -> tuple[str, bool, EvaluationReport | None]:
    """Run a single dataset evaluation.

    Returns (name, success, report).
    """
    if verbose:
        print(f"\nRunning evaluation: {discovered.name}")
    else:
        print(f"Running {discovered.name}...", end=" ")

    try:
        report = await discovered.dataset.evaluate(discovered.target_func)

        report.print(
            include_input=print_options.include_input,
            include_output=print_options.include_output,
            include_evaluator_failures=print_options.include_evaluator_failures,
            include_reasons=print_options.include_reasons,
        )

        if discovered.scorers:
            success = all(scorer(report, min_assertions) for scorer in discovered.scorers)
        else:
            success = average_assertions(report, min_assertions)

        if not verbose:
            status = "PASSED" if success else "FAILED"
            avg = report.averages()
            score_str = f"{avg.assertions:.3f}" if avg and avg.assertions is not None else "N/A"
            print(f"{status} ({score_str})")

        return discovered.name, success, report

    except Exception as e:
        if verbose:
            print(f"Error running evaluation {discovered.name}: {e}")
        else:
            print(f"ERROR ({e})")
        return discovered.name, False, None


async def run_all_evaluations(datasets: list[DiscoveredDataset], print_options: PrintOptions, min_assertions: float = 1.0, verbose: bool = False) -> bool:
    """Run all discovered datasets and print summary.

    Returns True if all evaluations pass.
    """
    results = []
    for dataset in datasets:
        result = await run_evaluation(dataset, print_options, min_assertions, verbose)
        results.append(result)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    failed = [(name, _, _) for name, success, _ in results if not success]

    if verbose:
        print(f"\n{'=' * 60}")
        print("EVALUATION SUMMARY")
        print(f"{'=' * 60}")
        for name, success, _ in results:
            status = "PASSED" if success else "FAILED"
            print(f"  {name}: {status}")
        print(f"\nTotal: {passed}/{total} evaluations passed")
    elif failed:
        print("\nFailed evaluations:")
        for name, _, _ in failed:
            print(f"  {name}")

    if passed < total:
        print(f"\n{total - passed} evaluation(s) failed")
        return False
    print("\nAll evaluations passed!")
    return True
