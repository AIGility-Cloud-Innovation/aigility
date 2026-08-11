"""Session-ID generation seam.

Providers and chat callers never generate session IDs themselves.  Keeping the
generator behind a small protocol makes UUIDv7/ULID migration possible without
changing the conversation or memory contracts.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class SessionIdGenerator(Protocol):
    """Generate one globally unique, opaque conversation identifier."""

    def new_id(self) -> str:
        """Return a new session ID."""


@dataclass(frozen=True)
class UUID4SessionIdGenerator:
    """Default generator compatible with Python 3.8 and newer."""

    prefix: str = "sess_"

    def __post_init__(self) -> None:
        if not self.prefix or not self.prefix.strip():
            raise ValueError("session ID 前缀不能为空")

    def new_id(self) -> str:
        """Return an opaque ID without user or agent information."""

        return f"{self.prefix}{uuid4().hex}"
