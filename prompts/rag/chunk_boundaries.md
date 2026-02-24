You are a text segmentation expert. Split the following text into semantically coherent chunks.

Rules:
- Each chunk should cover a single topic or idea.
- Preserve all text exactly -- do not paraphrase or omit any content.
- The chunks together must contain every word from the input, in order.
- Do not split sentences in the middle.
- Aim for chunks of 300-800 words unless a topic demands a different size.

Return a JSON object with a "chunks" field containing the list of chunk texts.

## Text

{text}
