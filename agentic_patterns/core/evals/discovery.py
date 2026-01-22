"""Dataset discovery functionality for agent evaluations.

This module handles discovering and loading Dataset objects from eval_*.py files
using naming conventions (dataset_*, target_*, scorer_*).
"""

import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from pydantic_evals.dataset import Dataset
from pydantic_evals.reporting import EvaluationReport


@dataclass
class DiscoveredDataset:
    """Bundle of dataset, target function, scorers, and metadata."""

    dataset: Dataset
    target_func: Callable
    scorers: list[Callable[[EvaluationReport, float], bool]]
    name: str
    file_path: Path


def find_eval_files(evals_dir: Path) -> list[Path]:
    """Find all eval_*.py files in the specified directory."""
    if not evals_dir.exists():
        print(f"Error: Evals directory '{evals_dir}' does not exist")
        sys.exit(1)

    eval_files = sorted(evals_dir.glob("eval_*.py"))
    if not eval_files:
        print(f"No eval_*.py files found in '{evals_dir}'")
        sys.exit(1)

    return eval_files


def load_module_from_file(file_path: Path) -> ModuleType:
    """Dynamically import a Python module from a file path."""
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _find_prefixed_objects(module: ModuleType, prefix: str, predicate: Callable[[Any], bool]) -> list[tuple[str, Any]]:
    """Find all objects with a specific prefix matching a predicate."""
    results = []
    for name, obj in inspect.getmembers(module):
        if name.startswith(prefix) and predicate(obj):
            results.append((name, obj))
    return results


def _find_datasets(module: ModuleType) -> list[tuple[str, Dataset]]:
    """Find all dataset_* objects that are Dataset instances."""
    return _find_prefixed_objects(module, "dataset_", lambda obj: isinstance(obj, Dataset))


def _find_target_functions(module: ModuleType) -> list[tuple[str, Callable]]:
    """Find all target_* functions (sync or async)."""
    return _find_prefixed_objects(module, "target_", lambda obj: inspect.isfunction(obj) or inspect.iscoroutinefunction(obj))


def _find_scorer_functions(module: ModuleType) -> list[tuple[str, Callable]]:
    """Find all scorer_* functions."""
    return _find_prefixed_objects(module, "scorer_", lambda obj: inspect.isfunction(obj) or inspect.iscoroutinefunction(obj))


def _matches_filter(module_name: str, file_name: str, dataset_name: str, name_filter: str | None) -> bool:
    """Check if the dataset matches the name filter."""
    if name_filter is None:
        return True
    full_name = f"{module_name}.{dataset_name}"
    return name_filter in module_name or name_filter in file_name or name_filter in dataset_name or name_filter in full_name


def discover_datasets(eval_files: list[Path], name_filter: str | None = None, verbose: bool = False) -> list[DiscoveredDataset]:
    """Discover all datasets from eval files.

    For each eval file, finds dataset_* objects and pairs them with target_* functions
    and scorer_* functions. Returns a list of DiscoveredDataset bundles.
    """
    all_datasets = []

    for eval_file in eval_files:
        if verbose:
            print(f"Processing file: {eval_file}")

        try:
            module = load_module_from_file(eval_file)
        except Exception as e:
            if verbose:
                print(f"  Error loading {eval_file}: {e}")
            continue

        datasets = _find_datasets(module)
        targets = _find_target_functions(module)
        scorers = _find_scorer_functions(module)

        if verbose:
            print(f"  Found {len(datasets)} datasets, {len(targets)} targets, {len(scorers)} scorers")

        if len(targets) != 1:
            if verbose:
                print(f"  Skipping file: expected 1 target function, found {len(targets)}")
            continue

        target_name, target_func = targets[0]
        scorer_funcs = [func for _, func in scorers]

        for dataset_name, dataset in datasets:
            if not _matches_filter(module.__name__, eval_file.stem, dataset_name, name_filter):
                if verbose:
                    print(f"    Skipping {dataset_name} (doesn't match filter)")
                continue

            full_name = f"{eval_file.stem}.{dataset_name}"
            discovered = DiscoveredDataset(
                dataset=dataset,
                target_func=target_func,
                scorers=scorer_funcs,
                name=full_name,
                file_path=eval_file,
            )
            all_datasets.append(discovered)
            if verbose:
                print(f"    Including {dataset_name}")

    if not all_datasets:
        print("No datasets found to evaluate")
        if verbose:
            print("This could be because:")
            print("  - No eval_*.py files contain dataset_* objects")
            print("  - The filter excluded all datasets")
            print("  - Files are missing exactly one target_* function")
        sys.exit(1)

    if verbose:
        print(f"\nFound {len(all_datasets)} datasets to evaluate")
    return all_datasets
