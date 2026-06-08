"""Embedding Cache Inspector."""

from .audit import AuditOptions, AuditResult, audit_records
from .loaders import SchemaOptions, load_jsonl, load_sqlite

__all__ = [
    "AuditOptions",
    "AuditResult",
    "SchemaOptions",
    "audit_records",
    "load_jsonl",
    "load_sqlite",
]

__version__ = "0.2.0"
