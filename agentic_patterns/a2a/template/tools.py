"""Template A2A server tools."""


def reverse_text(text: str) -> str:
    """Reverse the given text."""
    return text[::-1]


def char_count(text: str) -> int:
    """Count the number of characters in the given text."""
    return len(text)


def to_uppercase(text: str) -> str:
    """Convert the given text to uppercase."""
    return text.upper()


ALL_TOOLS = [reverse_text, char_count, to_uppercase]
