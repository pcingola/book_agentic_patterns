"""Network mode selection for sandbox containers based on PrivateData state."""

from enum import Enum

from agentic_patterns.core.compliance.private_data import session_has_private_data


class NetworkMode(str, Enum):
    """Docker network modes for sandbox containers."""
    FULL = "bridge"
    NONE = "none"


def get_network_mode(user_id: str, session_id: str) -> NetworkMode:
    """Return NONE if the session has private data, FULL otherwise."""
    if session_has_private_data(user_id, session_id):
        return NetworkMode.NONE
    return NetworkMode.FULL
