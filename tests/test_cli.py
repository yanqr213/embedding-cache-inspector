from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
