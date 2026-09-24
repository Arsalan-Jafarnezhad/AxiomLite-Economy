"""
SQLite connection + schema management.

Schema:
    users(id, name UNIQUE)
    transactions(
        id, amount, is_income, date, reason, user_id -> users.id,
        asset_type, asset_quantity
    )

`asset_type` / `asset_quantity` mark a transaction as an investment
transfer (buying/selling USDT or GOLD) rather than ordinary spending -
see economy.core for how that distinction is used. Dates are stored as
ISO strings: "YYYY-MM-DD".
"""

import sqlite3
from pathlib import Path

from .config import DB_PATH

# Columns added after the original schema shipped. Kept as a list of
# (name, sql_type) so _migrate_schema() can add any that are missing
# from an existing (older) database file without losing its data.
_ASSET_COLUMNS = [
    ("asset_type", "TEXT"),
    ("asset_quantity", "REAL"),
]


class Database:
    """Thin SQLite connection + schema manager."""

    def __init__(self, db_path: Path | str = DB_PATH):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._migrate_schema()

    def _create_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                amount         REAL NOT NULL,
                is_income      INTEGER NOT NULL,
                date           TEXT NOT NULL,
                reason         TEXT,
                user_id        INTEGER,
                asset_type     TEXT,
                asset_quantity REAL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
            """
        )
        self.conn.commit()

    def _migrate_schema(self) -> None:
        """
        Add any columns that a database created by an older version of
        the app is missing, without touching existing rows.
        """
        existing_columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(transactions)")
        }
        for column_name, column_type in _ASSET_COLUMNS:
            if column_name not in existing_columns:
                self.conn.execute(
                    f"ALTER TABLE transactions ADD COLUMN {column_name} {column_type}"
                )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
