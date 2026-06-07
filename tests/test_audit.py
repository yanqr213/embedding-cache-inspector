from __future__ import annotations

import math
import unittest

from embedding_cache_inspector.audit import AuditOptions, audit_records
from embedding_cache_inspector.models import CacheRecord


def record(
    document_id: str | None,
    chunk: str | None,
    embedding: list[float],
    model: str | None = "m",
    metadata: dict | None = None,
) -> CacheRecord:
    return CacheRecord(
        source="test",
        position=document_id or "missing",
        document_id=document_id,
        chunk=chunk,
        embedding=embedding,
        model=model,
        metadata=metadata or {},
    )


class AuditTests(unittest.TestCase):
    def test_detects_core_rules(self) -> None:
        result = audit_records(
            [
                record("a", "same chunk", [1.0, 2.0, 3.0], metadata={"source": "x"}),
                record("a", "same chunk", [1.0, 2.0, 3.0], metadata={}),
                record("b", "bad", [math.nan], model="other", metadata={"source": "x"}),
                record(None, "", [], metadata={}),
            ],
            AuditOptions(expected_dimension=3, required_metadata=("source",)),
        )
        codes = {finding.code for finding in result.findings}

        self.assertIn("duplicate_chunk_hash", codes)
        self.assertIn("duplicate_embedding_hash", codes)
        self.assertIn("duplicate_document_id", codes)
        self.assertIn("missing_required_metadata", codes)
        self.assertIn("dimension_mismatch", codes)
        self.assertIn("non_finite_embedding_value", codes)
        self.assertIn("empty_embedding", codes)
        self.assertIn("mixed_models", codes)
        self.assertEqual(result.dimension_stats["distribution"]["3"], 2)


if __name__ == "__main__":
    unittest.main()
