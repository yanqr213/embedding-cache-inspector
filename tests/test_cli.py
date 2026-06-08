from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_cli_inspect_jsonl_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "a",
                        "chunk": "hello",
                        "embedding": [1, 2, 3],
                        "model": "m",
                        "metadata": {"source": "x"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embedding_cache_inspector.cli",
                    "inspect",
                    "jsonl",
                    str(path),
                    "--expected-dimension",
                    "3",
                    "--format",
                    "json",
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["summary"]["records"], 1)
        self.assertEqual(payload["summary"]["errors"], 0)

    def test_cli_writes_junit_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "cache.jsonl"
            report = root / "reports" / "cache.xml"
            path.write_text(
                json.dumps(
                    {
                        "id": "a",
                        "chunk": "hello",
                        "embedding": [1, 2],
                        "model": "m",
                        "metadata": {"source": "x"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embedding_cache_inspector.cli",
                    "inspect",
                    "jsonl",
                    str(path),
                    "--expected-dimension",
                    "3",
                    "--format",
                    "junit",
                    "--report",
                    str(report),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(completed.returncode, 1, completed.stderr)
            suite = ET.fromstring(report.read_text(encoding="utf-8"))
            self.assertEqual(suite.attrib["failures"], "1")
            self.assertEqual(suite.find("testcase/failure").attrib["type"], "dimension_mismatch")

    def test_schema_options_command(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "embedding_cache_inspector.cli", "schema", "options"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--expected-dimension", completed.stdout)

    def test_version_command(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "embedding_cache_inspector.cli", "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("embedding-cache-inspector 0.2.0", completed.stdout)


if __name__ == "__main__":
    unittest.main()
