from __future__ import annotations

import json
import unittest

from embedding_cache_inspector.audit import audit_records
from embedding_cache_inspector.models import CacheRecord
from embedding_cache_inspector.reporter import render_json, render_markdown


class ReporterTests(unittest.TestCase):
    def test_renders_json_and_markdown(self) -> None:
        result = audit_records(
            [
                CacheRecord(
                    source="test",
                    position="1",
                    document_id="a",
                    chunk="hello",
                    embedding=[1.0, 2.0],
                    model="m",
                    metadata={},
                )
            ]
        )
        json_report = json.loads(render_json(result))
        markdown_report = render_markdown(result)

        self.assertEqual(json_report["summary"]["records"], 1)
        self.assertIn("# Embedding Cache Inspector Report", markdown_report)
        self.assertIn("Dimension Stats", markdown_report)


if __name__ == "__main__":
    unittest.main()
