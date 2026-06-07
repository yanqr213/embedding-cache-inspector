from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from embedding_cache_inspector.loaders import SchemaOptions, load_sqlite


class SqliteLoaderTests(unittest.TestCase):
    def test_loads_sqlite_rows_with_custom_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.sqlite"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "CREATE TABLE cache (doc_id TEXT, text TEXT, vector TEXT, model_name TEXT, meta TEXT)"
                )
                connection.execute(
                    "INSERT INTO cache VALUES (?, ?, ?, ?, ?)",
                    ("a", "hello", json.dumps([1, 2, 3]), "m", json.dumps({"source": "x"})),
                )
                connection.commit()
            result = load_sqlite(
                path,
                SchemaOptions(
                    sqlite_table="cache",
                    id_column="doc_id",
                    chunk_column="text",
                    embedding_column="vector",
                    model_column="model_name",
                    metadata_column="meta",
                ),
            )

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.findings, [])
        self.assertEqual(result.records[0].position, "rowid:1")
        self.assertEqual(result.records[0].metadata["source"], "x")


if __name__ == "__main__":
    unittest.main()
