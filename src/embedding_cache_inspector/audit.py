from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from .models import CacheRecord, Finding


@dataclass(frozen=True)
class AuditOptions:
    expected_dimension: int | None = None
    required_metadata: tuple[str, ...] = ()
    allow_mixed_models: bool = False


@dataclass
class AuditResult:
    records_count: int
    findings: list[Finding] = field(default_factory=list)
    dimension_stats: dict[str, Any] = field(default_factory=dict)
    model_distribution: dict[str, int] = field(default_factory=dict)
    duplicate_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def errors_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "error")

    @property
    def warnings_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "warning")

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "records": self.records_count,
                "errors": self.errors_count,
                "warnings": self.warnings_count,
            },
            "dimension_stats": self.dimension_stats,
            "model_distribution": self.model_distribution,
            "duplicate_summary": self.duplicate_summary,
            "findings": [finding.as_dict() for finding in self.findings],
        }


def audit_records(
    records: list[CacheRecord],
    options: AuditOptions | None = None,
    initial_findings: list[Finding] | None = None,
) -> AuditResult:
    options = options or AuditOptions()
    findings = list(initial_findings or [])

    dimensions = [len(record.embedding) for record in records]
    model_counter = Counter(record.model or "<missing>" for record in records)
    chunk_hash_to_records: dict[str, list[CacheRecord]] = defaultdict(list)
    embedding_hash_to_records: dict[str, list[CacheRecord]] = defaultdict(list)
    id_counter = Counter(record.document_id or "<missing>" for record in records)

    for record in records:
        _audit_record(record, options, findings)
        if record.chunk:
            chunk_hash_to_records[_hash_text(record.chunk)].append(record)
        if record.embedding:
            embedding_hash_to_records[_hash_embedding(record.embedding)].append(record)

    if options.expected_dimension is None:
        for dimension, count in Counter(dimensions).items():
            if dimension and count < len(records):
                findings.append(
                    Finding(
                        severity="warning",
                        code="dimension_mixed",
                        message=f"Embedding dimension {dimension} appears in {count} records.",
                        suggestion="Use one embedding model or rebuild inconsistent cache rows.",
                        details={"dimension": dimension, "count": count},
                    )
                )
    else:
        for record in records:
            actual = len(record.embedding)
            if actual != options.expected_dimension:
                findings.append(
                    Finding(
                        severity="error",
                        code="dimension_mismatch",
                        message=(
                            f"Embedding dimension is {actual}, expected "
                            f"{options.expected_dimension}."
                        ),
                        source=record.source,
                        position=record.position,
                        suggestion="Regenerate this embedding with the expected model.",
                        details={
                            "actual_dimension": actual,
                            "expected_dimension": options.expected_dimension,
                            "document_id": record.document_id,
                        },
                    )
                )

    if len(model_counter) > 1 and not options.allow_mixed_models:
        findings.append(
            Finding(
                severity="warning",
                code="mixed_models",
                message="Cache contains embeddings from multiple or missing models.",
                suggestion="Separate caches by model or rebuild with one model per index.",
                details={"models": dict(model_counter)},
            )
        )

    duplicate_summary = _audit_duplicates(
        findings,
        chunk_hash_to_records,
        embedding_hash_to_records,
        id_counter,
    )
    return AuditResult(
        records_count=len(records),
        findings=findings,
        dimension_stats=_dimension_stats(dimensions),
        model_distribution=dict(model_counter),
        duplicate_summary=duplicate_summary,
    )


def _audit_record(
    record: CacheRecord,
    options: AuditOptions,
    findings: list[Finding],
) -> None:
    if not record.document_id:
        findings.append(
            Finding(
                severity="error",
                code="missing_document_id",
                message="Record is missing a document id.",
                source=record.source,
                position=record.position,
                suggestion="Populate the configured id field for traceability.",
            )
        )
    if not record.chunk:
        findings.append(
            Finding(
                severity="error",
                code="missing_chunk",
                message="Record is missing chunk text.",
                source=record.source,
                position=record.position,
                suggestion="Store the exact embedded chunk text for auditability.",
            )
        )
    if record.embedding_parse_error:
        findings.append(
            Finding(
                severity="error",
                code="embedding_parse_error",
                message=record.embedding_parse_error,
                source=record.source,
                position=record.position,
                suggestion="Store embeddings as JSON arrays or comma-separated numbers.",
            )
        )
    if record.metadata_parse_error:
        findings.append(
            Finding(
                severity="warning",
                code="metadata_parse_error",
                message=record.metadata_parse_error,
                source=record.source,
                position=record.position,
                suggestion="Store metadata as a JSON object.",
            )
        )
    if not record.embedding:
        findings.append(
            Finding(
                severity="error",
                code="empty_embedding",
                message="Embedding vector is empty.",
                source=record.source,
                position=record.position,
                suggestion="Regenerate this embedding or remove the row.",
                details={"document_id": record.document_id},
            )
        )
    else:
        bad_values = [
            index
            for index, value in enumerate(record.embedding)
            if math.isnan(value) or math.isinf(value)
        ]
        if bad_values:
            findings.append(
                Finding(
                    severity="error",
                    code="non_finite_embedding_value",
                    message="Embedding contains NaN or Infinity values.",
                    source=record.source,
                    position=record.position,
                    suggestion="Regenerate this embedding; non-finite vectors break similarity search.",
                    details={"indexes": bad_values, "document_id": record.document_id},
                )
            )
    for field_name in options.required_metadata:
        if field_name not in record.metadata or record.metadata.get(field_name) in (None, ""):
            findings.append(
                Finding(
                    severity="warning",
                    code="missing_required_metadata",
                    message=f"Metadata field '{field_name}' is missing or empty.",
                    source=record.source,
                    position=record.position,
                    suggestion=f"Add metadata.{field_name} to support filtering and lineage.",
                    details={"field": field_name, "document_id": record.document_id},
                )
            )


def _audit_duplicates(
    findings: list[Finding],
    chunk_hash_to_records: dict[str, list[CacheRecord]],
    embedding_hash_to_records: dict[str, list[CacheRecord]],
    id_counter: Counter[str],
) -> dict[str, Any]:
    duplicate_chunk_hashes = {
        item_hash: records
        for item_hash, records in chunk_hash_to_records.items()
        if len(records) > 1
    }
    duplicate_embedding_hashes = {
        item_hash: records
        for item_hash, records in embedding_hash_to_records.items()
        if len(records) > 1
    }
    duplicate_ids = {
        document_id: count
        for document_id, count in id_counter.items()
        if document_id != "<missing>" and count > 1
    }
    for item_hash, records in duplicate_chunk_hashes.items():
        findings.append(
            Finding(
                severity="warning",
                code="duplicate_chunk_hash",
                message=f"Chunk text hash appears {len(records)} times.",
                suggestion="Deduplicate identical chunks or confirm the duplicate is intentional.",
                details={
                    "hash": item_hash,
                    "locations": [_location(record) for record in records],
                },
            )
        )
    for item_hash, records in duplicate_embedding_hashes.items():
        findings.append(
            Finding(
                severity="warning",
                code="duplicate_embedding_hash",
                message=f"Embedding vector hash appears {len(records)} times.",
                suggestion="Check whether repeated vectors came from duplicated chunks or failed embedding calls.",
                details={
                    "hash": item_hash,
                    "locations": [_location(record) for record in records],
                },
            )
        )
    for document_id, count in duplicate_ids.items():
        findings.append(
            Finding(
                severity="warning",
                code="duplicate_document_id",
                message=f"Document id '{document_id}' appears {count} times.",
                suggestion="Use stable chunk ids or add chunk indexes when one document has multiple chunks.",
                details={"document_id": document_id, "count": count},
            )
        )
    return {
        "duplicate_chunk_hashes": len(duplicate_chunk_hashes),
        "duplicate_embedding_hashes": len(duplicate_embedding_hashes),
        "duplicate_document_ids": len(duplicate_ids),
    }


def _dimension_stats(dimensions: list[int]) -> dict[str, Any]:
    if not dimensions:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "distribution": {},
        }
    return {
        "count": len(dimensions),
        "min": min(dimensions),
        "max": max(dimensions),
        "mean": mean(dimensions),
        "distribution": {str(key): value for key, value in sorted(Counter(dimensions).items())},
    }


def _hash_text(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _hash_embedding(values: list[float]) -> str:
    normalized = ",".join(f"{value:.12g}" for value in values)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _location(record: CacheRecord) -> dict[str, str | None]:
    return {
        "source": record.source,
        "position": record.position,
        "document_id": record.document_id,
    }
