from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from embedding_cache_inspector.loaders import SchemaOptions, load_jsonl


class JsonlLoaderTests(unittest.TestCase):
    def test_loads_records_and_reports_bad_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "doc_id": "a",
                                "text": "hello",
                                "vector": [1, 2, 3],
                                "model_name": "m",
                                "meta": {"source": "x"},
                            }
                        ),
                        "not-json",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = load_jsonl(
                path,
                SchemaOptions(
                    id_field="doc_id",
                    chunk_field="text",
                    embedding_field="vector",
                    model_field="model_name",
                    metadata_field="meta",
                ),
            )

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].document_id, "a")
        self.assertEqual(result.records[0].embedding, [1.0, 2.0, 3.0])
        self.assertEqual([finding.code for finding in result.findings], ["invalid_json"])


if __name__ == "__main__":
    unittest.main()
