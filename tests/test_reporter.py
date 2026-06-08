from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET

from embedding_cache_inspector.audit import audit_records
from embedding_cache_inspector.models import CacheRecord, Finding
from embedding_cache_inspector.reporter import render_json, render_junit, render_markdown


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

    def test_renders_junit_failures_and_warnings(self) -> None:
        result = audit_records(
            [],
            initial_findings=[
                Finding("error", "empty_embedding", "Embedding vector is empty.", source="cache.jsonl", position="2"),
                Finding("warning", "mixed_models", "Cache contains multiple models."),
            ],
        )
        suite = ET.fromstring(render_junit(result))

        self.assertEqual(suite.tag, "testsuite")
        self.assertEqual(suite.attrib["tests"], "2")
        self.assertEqual(suite.attrib["failures"], "1")
        self.assertEqual(suite.findall("testcase")[0].find("failure").attrib["type"], "empty_embedding")
        self.assertIn("mixed_models", suite.findall("testcase")[1].findtext("system-out"))

    def test_renders_junit_pass_when_clean(self) -> None:
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
        suite = ET.fromstring(render_junit(result))

        self.assertEqual(suite.attrib["tests"], "1")
        self.assertEqual(suite.attrib["failures"], "0")
        self.assertEqual(suite.find("testcase").attrib["name"], "cache.clean")


if __name__ == "__main__":
    unittest.main()
