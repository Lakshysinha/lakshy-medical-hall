from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SqliteStateStore:
    """Simple SQLite-backed key/value state store for PharmacyService."""

    def __init__(self, db_path: str) -> None:
        self.db_path = str(Path(db_path))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    state_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def load(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT state_json FROM app_state WHERE id = 1").fetchone()
        if row is None:
            return None
        return json.loads(row["state_json"])

    def save(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_state (id, state_json)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET state_json = excluded.state_json
                """,
                (payload,),
            )
            conn.commit()
