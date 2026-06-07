from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .models import CacheRecord, Finding


@dataclass(frozen=True)
class SchemaOptions:
    id_field: str = "id"
    chunk_field: str = "chunk"
    embedding_field: str = "embedding"
    model_field: str = "model"
    metadata_field: str = "metadata"
    sqlite_table: str = "embeddings"
    id_column: str = "id"
    chunk_column: str = "chunk"
    embedding_column: str = "embedding"
    model_column: str = "model"
    metadata_column: str = "metadata"


@dataclass(frozen=True)
class LoadResult:
    records: list[CacheRecord]
    findings: list[Finding]


def load_jsonl(path: str | Path, schema: SchemaOptions | None = None) -> LoadResult:
    schema = schema or SchemaOptions()
    file_path = Path(path)
    records: list[CacheRecord] = []
    findings: list[Finding] = []

    with file_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                findings.append(
                    Finding(
                        severity="warning",
                        code="blank_line",
                        message="JSONL contains a blank line.",
                        source=str(file_path),
                        position=str(line_no),
                        suggestion="Remove blank lines or regenerate the cache file.",
                    )
                )
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                findings.append(
                    Finding(
                        severity="error",
                        code="invalid_json",
                        message=f"Line is not valid JSON: {exc.msg}.",
                        source=str(file_path),
                        position=str(line_no),
                        suggestion="Fix or remove the malformed JSONL entry.",
                    )
                )
                continue
            if not isinstance(payload, dict):
                findings.append(
                    Finding(
                        severity="error",
                        code="record_not_object",
                        message="JSONL line must contain an object.",
                        source=str(file_path),
                        position=str(line_no),
                        suggestion="Store each embedding cache row as a JSON object.",
                    )
                )
                continue
            records.append(_record_from_mapping(payload, str(file_path), str(line_no), schema))

    return LoadResult(records=records, findings=findings)


def load_sqlite(path: str | Path, schema: SchemaOptions | None = None) -> LoadResult:
    schema = schema or SchemaOptions()
    db_path = Path(path)
    records: list[CacheRecord] = []
    findings: list[Finding] = []

    selected = [
        schema.id_column,
        schema.chunk_column,
        schema.embedding_column,
        schema.model_column,
        schema.metadata_column,
    ]
    sql = (
        "SELECT rowid AS __rowid__, "
        + ", ".join(_quote_identifier(column) for column in selected)
        + f" FROM {_quote_identifier(schema.sqlite_table)}"
    )

    try:
        with closing(sqlite3.connect(str(db_path))) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(sql)
            for row in cursor:
                payload = {
                    schema.id_field: row[schema.id_column],
                    schema.chunk_field: row[schema.chunk_column],
                    schema.embedding_field: row[schema.embedding_column],
                    schema.model_field: row[schema.model_column],
                    schema.metadata_field: row[schema.metadata_column],
                }
                records.append(
                    _record_from_mapping(
                        payload,
                        str(db_path),
                        f"rowid:{row['__rowid__']}",
                        schema,
                    )
                )
            cursor.close()
    except sqlite3.Error as exc:
        findings.append(
            Finding(
                severity="error",
                code="sqlite_read_error",
                message=f"Could not read SQLite cache: {exc}.",
                source=str(db_path),
                suggestion="Check the database path, table name, and column options.",
                details={"table": schema.sqlite_table, "columns": selected},
            )
        )

    return LoadResult(records=records, findings=findings)


def _record_from_mapping(
    payload: dict[str, Any],
    source: str,
    position: str,
    schema: SchemaOptions,
) -> CacheRecord:
    embedding, embedding_error = _parse_embedding(payload.get(schema.embedding_field))
    metadata, metadata_error = _parse_metadata(payload.get(schema.metadata_field))
    return CacheRecord(
        source=source,
        position=position,
        document_id=_to_optional_string(payload.get(schema.id_field)),
        chunk=_to_optional_string(payload.get(schema.chunk_field)),
        embedding=embedding,
        model=_to_optional_string(payload.get(schema.model_field)),
        metadata=metadata,
        raw=payload,
        embedding_parse_error=embedding_error,
        metadata_parse_error=metadata_error,
    )


def _parse_embedding(value: Any) -> tuple[list[float], str | None]:
    if value is None:
        return [], "embedding is missing"
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            return [], f"embedding bytes are not UTF-8: {exc}"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return [], None
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = [part.strip() for part in text.split(",") if part.strip()]
    if not isinstance(value, Iterable) or isinstance(value, (dict, str)):
        return [], "embedding is not a list or JSON array"

    numbers: list[float] = []
    for index, item in enumerate(value):
        try:
            numbers.append(float(item))
        except (TypeError, ValueError):
            return numbers, f"embedding value at index {index} is not numeric"
    return numbers, None


def _parse_metadata(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None or value == "":
        return {}, None
    if isinstance(value, dict):
        return value, None
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            return {}, f"metadata bytes are not UTF-8: {exc}"
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            return {}, f"metadata is not valid JSON: {exc.msg}"
        if isinstance(decoded, dict):
            return decoded, None
        return {}, "metadata JSON is not an object"
    return {}, "metadata is not an object"


def _to_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _quote_identifier(identifier: str) -> str:
    if "\x00" in identifier:
        raise ValueError("SQLite identifier contains NUL byte")
    return '"' + identifier.replace('"', '""') + '"'
