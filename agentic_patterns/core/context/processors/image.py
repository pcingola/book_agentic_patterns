"""Image file processor with resizing for attachment limits."""

import io
from pathlib import Path

from agentic_patterns.core.context.config import (
    IMAGE_ATTACHMENT_TYPES,
    ContextConfig,
    load_context_config,
)
from agentic_patterns.core.context.models import (
    BinaryContent,
    FileExtractionResult,
    FileMetadata,
    FileType,
    TruncationInfo,
)
from agentic_patterns.core.context.processors.common import (
    create_error_result,
    create_file_metadata,
)


def _resize_image(
    image, max_size: int | None = None, max_dimension: int | None = None
) -> tuple:
    """Resize image based on file size or dimensions. Returns (resized_image, was_resized)."""
    from PIL import Image

    if max_dimension is not None:
        if image.width <= max_dimension and image.height <= max_dimension:
            return image, False

        ratio = min(max_dimension / image.width, max_dimension / image.height)
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized, True

    if max_size is not None:
        buffer = io.BytesIO()
        image.save(buffer, format=image.format or "PNG")
        current_size = buffer.tell()

        if current_size <= max_size:
            return image, False

        resize_ratio = (max_size / current_size) ** 0.5
        new_width = int(image.width * resize_ratio)
        new_height = int(image.height * resize_ratio)

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized, True

    return image, False


def process_image(
    file_path: Path,
    max_size: int | None = None,
    max_dimension: int | None = None,
    config: ContextConfig | None = None,
) -> FileExtractionResult:
    """Process image files and resize if needed."""
    if config is None:
        config = load_context_config()

    if max_size is None and max_dimension is None:
        max_size = config.max_image_size_bytes

    try:
        from PIL import Image
    except ImportError:
        return create_error_result(
            ImportError(
                "pillow is required for image processing. Install with: uv add pillow"
            ),
            FileType.IMAGE,
            file_path,
            "image (missing dependencies)",
        )

    try:
        with Image.open(file_path) as image:
            image_format = image.format
            mime_type = f"image/{image_format.lower()}" if image_format else "image/png"

            if mime_type not in IMAGE_ATTACHMENT_TYPES:
                return FileExtractionResult(
                    content=None,
                    success=False,
                    error_message=f"Unsupported image type: {mime_type}",
                    file_type=FileType.IMAGE,
                    metadata=FileMetadata(
                        size_bytes=file_path.stat().st_size, mime_type=mime_type
                    ),
                )

            metadata = create_file_metadata(file_path, mime_type=mime_type)

            processed_image, was_resized = _resize_image(
                image, max_size=max_size, max_dimension=max_dimension
            )

            buffer = io.BytesIO()
            processed_image.save(buffer, format=image_format or "PNG")
            image_data = buffer.getvalue()

            metadata.size_bytes = len(image_data)

            truncation_info = None
            if was_resized:
                lines_shown = f"{processed_image.width}x{processed_image.height} (resized from {image.width}x{image.height})"
                truncation_info = TruncationInfo(lines_shown=lines_shown)

            return FileExtractionResult(
                content=BinaryContent(data=image_data, mime_type=mime_type),
                success=True,
                file_type=FileType.IMAGE,
                truncation_info=truncation_info,
                metadata=metadata,
            )

    except Exception as e:
        return create_error_result(e, FileType.IMAGE, file_path, "image")
