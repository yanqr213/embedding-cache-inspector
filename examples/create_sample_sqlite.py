from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path


def main() -> None:
    path = Path(__file__).with_name("sample.sqlite")
    if path.exists():
        path.unlink()
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE embeddings (
                id TEXT,
                chunk TEXT,
                embedding TEXT,
                model TEXT,
                metadata TEXT
            )
            """
        )
        rows = [
            (
                "doc-1#0",
                "SQLite cache row.",
                json.dumps([0.1, 0.2, 0.3]),
                "text-embedding-3-small",
                json.dumps({"source": "sqlite.md", "language": "en"}),
            ),
            (
                "doc-2#0",
                "Bad dimension row.",
                json.dumps([0.1, 0.2]),
                "text-embedding-3-small",
                json.dumps({"source": "sqlite.md"}),
            ),
        ]
        connection.executemany("INSERT INTO embeddings VALUES (?, ?, ?, ?, ?)", rows)
        connection.commit()
    print(path)


if __name__ == "__main__":
    main()
