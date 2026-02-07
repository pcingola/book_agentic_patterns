# Image, Audio, Video & Document Input

Some LLMs are now capable of understanding audio, video, image and document content.

## Image Input

Info

Some models do not support image input. Please check the model's documentation to confirm whether it supports image input.

If you have a direct URL for the image, you can use ImageUrl:

[Learn about Gateway](https://ai.pydantic.dev/gateway) image_input.py

```python
from pydantic_ai import Agent, ImageUrl

agent = Agent(model='gateway/openai:gpt-5.2')
result = agent.run_sync(
    [
        'What company is this logo from?',
        ImageUrl(url='https://iili.io/3Hs4FMg.png'),
    ]
)
print(result.output)
#> This is the logo for Pydantic, a data validation and settings management library in Python.
```

image_input.py

```python
from pydantic_ai import Agent, ImageUrl

agent = Agent(model='openai:gpt-5.2')
result = agent.run_sync(
    [
        'What company is this logo from?',
        ImageUrl(url='https://iili.io/3Hs4FMg.png'),
    ]
)
print(result.output)
#> This is the logo for Pydantic, a data validation and settings management library in Python.
```

If you have the image locally, you can also use BinaryContent:

[Learn about Gateway](https://ai.pydantic.dev/gateway) local_image_input.py

```python
import httpx

from pydantic_ai import Agent, BinaryContent

image_response = httpx.get('https://iili.io/3Hs4FMg.png')  # Pydantic logo

agent = Agent(model='gateway/openai:gpt-5.2')
result = agent.run_sync(
    [
        'What company is this logo from?',
        BinaryContent(data=image_response.content, media_type='image/png'),  # (1)!
    ]
)
print(result.output)
#> This is the logo for Pydantic, a data validation and settings management library in Python.
```

1. To ensure the example is runnable we download this image from the web, but you can also use `Path().read_bytes()` to read a local file's contents.

local_image_input.py

```python
import httpx

from pydantic_ai import Agent, BinaryContent

image_response = httpx.get('https://iili.io/3Hs4FMg.png')  # Pydantic logo

agent = Agent(model='openai:gpt-5.2')
result = agent.run_sync(
    [
        'What company is this logo from?',
        BinaryContent(data=image_response.content, media_type='image/png'),  # (1)!
    ]
)
print(result.output)
#> This is the logo for Pydantic, a data validation and settings management library in Python.
```

1. To ensure the example is runnable we download this image from the web, but you can also use `Path().read_bytes()` to read a local file's contents.

## Audio Input

Info

Some models do not support audio input. Please check the model's documentation to confirm whether it supports audio input.

You can provide audio input using either AudioUrl or BinaryContent. The process is analogous to the examples above.

## Video Input

Info

Some models do not support video input. Please check the model's documentation to confirm whether it supports video input.

You can provide video input using either VideoUrl or BinaryContent. The process is analogous to the examples above.

## Document Input

Info

Some models do not support document input. Please check the model's documentation to confirm whether it supports document input.

You can provide document input using either DocumentUrl or BinaryContent. The process is similar to the examples above.

If you have a direct URL for the document, you can use DocumentUrl:

[Learn about Gateway](https://ai.pydantic.dev/gateway) document_input.py

```python
from pydantic_ai import Agent, DocumentUrl

agent = Agent(model='gateway/anthropic:claude-sonnet-4-5')
result = agent.run_sync(
    [
        'What is the main content of this document?',
        DocumentUrl(url='https://storage.googleapis.com/cloud-samples-data/generative-ai/pdf/2403.05530.pdf'),
    ]
)
print(result.output)
#> This document is the technical report introducing Gemini 1.5, Google's latest large language model...
```

document_input.py

```python
from pydantic_ai import Agent, DocumentUrl

agent = Agent(model='anthropic:claude-sonnet-4-5')
result = agent.run_sync(
    [
        'What is the main content of this document?',
        DocumentUrl(url='https://storage.googleapis.com/cloud-samples-data/generative-ai/pdf/2403.05530.pdf'),
    ]
)
print(result.output)
#> This document is the technical report introducing Gemini 1.5, Google's latest large language model...
```

The supported document formats vary by model.

You can also use BinaryContent to pass document data directly:

[Learn about Gateway](https://ai.pydantic.dev/gateway) binary_content_input.py

```python
from pathlib import Path
from pydantic_ai import Agent, BinaryContent

pdf_path = Path('document.pdf')
agent = Agent(model='gateway/anthropic:claude-sonnet-4-5')
result = agent.run_sync(
    [
        'What is the main content of this document?',
        BinaryContent(data=pdf_path.read_bytes(), media_type='application/pdf'),
    ]
)
print(result.output)
#> The document discusses...
```

binary_content_input.py

```python
from pathlib import Path
from pydantic_ai import Agent, BinaryContent

pdf_path = Path('document.pdf')
agent = Agent(model='anthropic:claude-sonnet-4-5')
result = agent.run_sync(
    [
        'What is the main content of this document?',
        BinaryContent(data=pdf_path.read_bytes(), media_type='application/pdf'),
    ]
)
print(result.output)
#> The document discusses...
```

## User-side download vs. direct file URL

When using one of `ImageUrl`, `AudioUrl`, `VideoUrl` or `DocumentUrl`, Pydantic AI will default to sending the URL to the model provider, so the file is downloaded on their side.

Support for file URLs varies depending on type and provider:

| Model                | Send URL directly                                                                                                                                                                | Download and send bytes               | Unsupported                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ----------------------------------------------- |
| OpenAIChatModel      | `ImageUrl`                                                                                                                                                                       | `AudioUrl`, `DocumentUrl`             | `VideoUrl`                                      |
| OpenAIResponsesModel | `ImageUrl`, `AudioUrl`, `DocumentUrl`                                                                                                                                            | â€”                                     | `VideoUrl`                                      |
| AnthropicModel       | `ImageUrl`, `DocumentUrl` (PDF)                                                                                                                                                  | `DocumentUrl` (`text/plain`)          | `AudioUrl`, `VideoUrl`                          |
| GoogleModel (Vertex) | All URL types                                                                                                                                                                    | â€”                                     | â€”                                               |
| GoogleModel (GLA)    | [YouTube](https://ai.pydantic.dev/models/google/#document-image-audio-and-video-input), [Files API](https://ai.pydantic.dev/models/google/#document-image-audio-and-video-input) | All other URLs                        | â€”                                               |
| XaiModel             | `ImageUrl`                                                                                                                                                                       | `DocumentUrl`                         | `AudioUrl`, `VideoUrl`                          |
| MistralModel         | `ImageUrl`, `DocumentUrl` (PDF)                                                                                                                                                  | â€”                                     | `AudioUrl`, `VideoUrl`, `DocumentUrl` (non-PDF) |
| BedrockConverseModel | S3 URLs (`s3://`)                                                                                                                                                                | `ImageUrl`, `DocumentUrl`, `VideoUrl` | `AudioUrl`                                      |
| OpenRouterModel      | `ImageUrl`, `DocumentUrl`                                                                                                                                                        | `AudioUrl`                            | `VideoUrl`                                      |

A model API may be unable to download a file (e.g., because of crawling or access restrictions) even if it supports file URLs. For example, GoogleModel on Vertex AI limits YouTube video URLs to one URL per request. In such cases, you can instruct Pydantic AI to download the file content locally and send that instead of the URL by setting `force_download` on the URL object:

force_download.py

```python
from pydantic_ai import ImageUrl, AudioUrl, VideoUrl, DocumentUrl

ImageUrl(url='https://example.com/image.png', force_download=True)
AudioUrl(url='https://example.com/audio.mp3', force_download=True)
VideoUrl(url='https://example.com/video.mp4', force_download=True)
DocumentUrl(url='https://example.com/doc.pdf', force_download=True)
```

## Uploaded Files

Some model providers support passing URLs to files hosted on their platform:

- GoogleModel supports the [Files API](https://ai.pydantic.dev/models/google/#document-image-audio-and-video-input) for uploading and referencing files.
- BedrockConverseModel supports `s3://<bucket-name>/<object-key>` URIs, provided that the assumed role has the `s3:GetObject` permission. An optional `bucketOwner` query parameter must be specified if the bucket is not owned by the account making the request. For example: `s3://my-bucket/my-file.png?bucketOwner=123456789012`.
