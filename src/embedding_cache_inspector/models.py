from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CacheRecord:
    """A normalized embedding cache entry."""

    source: str
    position: str
    document_id: str | None
    chunk: str | None
    embedding: list[float]
    model: str | None
    metadata: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)
    embedding_parse_error: str | None = None
    metadata_parse_error: str | None = None


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    source: str | None = None
    position: str | None = None
    suggestion: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.source is not None:
            data["source"] = self.source
        if self.position is not None:
            data["position"] = self.position
        if self.suggestion is not None:
            data["suggestion"] = self.suggestion
        if self.details:
            data["details"] = self.details
        return data
