"""XML file processor with structure truncation."""

import io
import json
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

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


def _parse_xml_to_dict(
    element: ET.Element, current_depth: int, max_depth: int
) -> dict | str:
    """Convert XML element to dictionary structure."""
    if current_depth > max_depth:
        return "... [max depth reached]"

    result = {}

    if element.attrib:
        result["@attributes"] = element.attrib

    if element.text and element.text.strip():
        if len(element) == 0 and not element.attrib:
            return element.text.strip()
        result["#text"] = element.text.strip()

    children = {}
    for child in element:
        child_data = _parse_xml_to_dict(child, current_depth + 1, max_depth)

        if child.tag in children:
            if not isinstance(children[child.tag], list):
                children[child.tag] = [children[child.tag]]
            children[child.tag].append(child_data)
        else:
            children[child.tag] = child_data

    if children:
        result.update(children)

    if len(result) == 1 and "#text" in result:
        return result["#text"]

    return result if result else None


def process_xml(
    file_path: Path,
    config: ContextConfig | None = None,
    tokenizer: Callable[[str], int] | None = None,
) -> FileExtractionResult:
    """Process XML files with structure truncation."""
    if config is None:
        config = load_context_config()

    try:
        metadata = create_file_metadata(file_path, mime_type="application/xml")

        tree = ET.parse(file_path)
        root = tree.getroot()

        data = {root.tag: _parse_xml_to_dict(root, 0, config.max_nesting_depth)}

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

        json_str = json.dumps(truncated_data, indent=2, ensure_ascii=False)
        output.write(json_str)
        output.write("\n</content>\n")

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
            file_type=FileType.XML,
            truncation_info=truncation_info,
            metadata=metadata,
        )

    except ET.ParseError as e:
        return create_error_result(e, FileType.XML, file_path, "XML (invalid XML)")
    except Exception as e:
        return create_error_result(e, FileType.XML, file_path, "XML")
