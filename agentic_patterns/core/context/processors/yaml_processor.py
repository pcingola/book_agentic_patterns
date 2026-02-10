"""YAML file processor with structure truncation."""

import io
from collections.abc import Callable
from pathlib import Path

import yaml

from agentic_patterns.core.context.config import ContextConfig, load_context_config
from agentic_patterns.core.context.models import (
    FileExtractionResult,
    FileType,
    TruncationInfo,
)
from agentic_patterns.core.context.processors.common import (
    check_and_apply_output_limit,
    create_error_result,
    create_file_metadata,
    format_truncation_summary,
    human_readable_size,
)
from agentic_patterns.core.context.processors.json_processor import (
    _format_truncation_stats,
    _truncate_structure,
)


def process_yaml(
    file_path: Path,
    config: ContextConfig | None = None,
    tokenizer: Callable[[str], int] | None = None,
) -> FileExtractionResult:
    """Process YAML files with structure truncation."""
    if config is None:
        config = load_context_config()

    try:
        metadata = create_file_metadata(file_path, mime_type="application/x-yaml")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        truncation_stats = {
            "array_truncations": 0,
            "object_truncations": 0,
            "object_length_truncations": 0,
            "string_truncations": 0,
            "depth_truncations": 0,
        }

        truncated_data = _truncate_structure(data, 0, config, truncation_stats)

        output = io.StringIO()
        output.write(f"File: {file_path.name}\n")
        output.write(f"Size: {human_readable_size(metadata.size_bytes)}\n\n")
        output.write("<content>\n")

        yaml_str = yaml.dump(
            truncated_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        output.write(yaml_str)
        output.write("</content>\n")

        truncation_info = TruncationInfo()

        if tokenizer:
            truncation_info.tokens_shown = tokenizer(output.getvalue())

        result_content = check_and_apply_output_limit(
            output.getvalue(), config.max_total_output, truncation_info
        )

        extra_stats = _format_truncation_stats(truncation_stats)
        summary = format_truncation_summary(truncation_info, extra_stats)
        if summary:
            result_content += summary

        return FileExtractionResult(
            content=result_content,
            success=True,
            file_type=FileType.YAML,
            truncation_info=truncation_info,
            metadata=metadata,
        )

    except yaml.YAMLError as e:
        return create_error_result(e, FileType.YAML, file_path, "YAML (invalid YAML)")
    except Exception as e:
        return create_error_result(e, FileType.YAML, file_path, "YAML")
