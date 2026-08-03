# Usage Tracking Types
"""
Token usage tracking and structured result types for RAG operations.

Provides data classes for tracking embedding/rerank token consumption
and returning structured search results.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token usage for a single API call type"""

    input_tokens: int = 0
    total_tokens: int = 0
    model: str = ""

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            model=self.model or other.model,
        )


class UsageStats(BaseModel):
    """Aggregated token usage across embedding, rerank, etc."""

    embedding: TokenUsage = Field(default_factory=TokenUsage)
    rerank: TokenUsage = Field(default_factory=TokenUsage)

    @property
    def total_tokens(self) -> int:
        return self.embedding.total_tokens + self.rerank.total_tokens

    def __add__(self, other: "UsageStats") -> "UsageStats":
        return UsageStats(
            embedding=self.embedding + other.embedding,
            rerank=self.rerank + other.rerank,
        )

    def __iadd__(self, other: "UsageStats") -> "UsageStats":
        self.embedding = self.embedding + other.embedding
        self.rerank = self.rerank + other.rerank
        return self

    def reset(self):
        self.embedding = TokenUsage()
        self.rerank = TokenUsage()


class SearchResult(BaseModel):
    """Structured search result with usage tracking"""

    content: str
    documents: List[Any] = Field(default_factory=list)
    usage: UsageStats = Field(default_factory=UsageStats)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return self.content

    def __bool__(self) -> bool:
        return bool(self.content)


class AddFileResult(BaseModel):
    """Result of add_file() with usage tracking"""

    file_hash: str
    file_name: str
    usage: UsageStats = Field(default_factory=UsageStats)

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)


__all__ = [
    "TokenUsage",
    "UsageStats",
    "SearchResult",
    "AddFileResult",
]
