"""
Economy logic, backed by SQLite (assets/data/database.sqlite3).

Schema:
    users(id, name UNIQUE)
    transactions(id, amount, is_income, date, reason, user_id -> users.id)

Dates are stored as ISO strings: "YYYY-MM-DD".

Every import format (.txt, .csv, .json, .toml, .yaml, .sql, .sqlite3/.db) is
normalized into a common list of plain dict "records" -
{"amount", "is_income", "date", "person", "reason"} - and funneled through a
single insertion routine, so each format only needs a small loader function.
"""

import csv
import json
import os
import re
import sqlite3
from time import strftime

from price import get_usd_irt

DB_PATH = os.path.join("assets", "data", "database.sqlite3")

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Matches ledger lines like:
#   + 500,000 [2026/06/21] [Father] [Monthly Income]
#   - 18,400 [2026/06/26] [Sepehr Jalil Jamshidi] [Payback Of Ice Cream]
_LEDGER_LINE_RE = re.compile(
    r"^\s*(?P<sign>[+-])\s*(?P<amount>[\d,]+(?:\.\d+)?)\s*(?P<rest>.*)$"
)
_TAG_RE = re.compile(r"\[(.*?)\]")


def _normalize_date(raw_date: str) -> str:
    """Convert "2026/06/21" (or already-ISO "2026-06-21") into "YYYY-MM-DD"."""
    return raw_date.strip().replace("/", "-")


def parse_ledger_line(line: str) -> dict | None:
    """
    Parse a single ".txt" ledger line into a record dict, or None if the
    line is blank/unparseable.
    """
    line = line.strip()
    if not line:
        return None

    match = _LEDGER_LINE_RE.match(line)
    if not match:
        return None

    tags = _TAG_RE.findall(match.group("rest"))
    raw_date = tags[0] if len(tags) > 0 else None
    if not raw_date:
        return None

    return {
        "amount": float(match.group("amount").replace(",", "")),
        "is_income": match.group("sign") == "+",
        "date": _normalize_date(raw_date),
        "person": tags[1].strip() if len(tags) > 1 and tags[1].strip() else None,
        "reason": tags[2].strip() if len(tags) > 2 else "",
    }


class Database:
    """Thin SQLite connection + schema manager."""

    def __init__(self, db_path: str = DB_PATH):
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self):
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
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                amount    REAL NOT NULL,
                is_income INTEGER NOT NULL,
                date      TEXT NOT NULL,
                reason    TEXT,
                user_id   INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
            """
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


class Economy:
    """Personal economy / money tracking, backed by SQLite."""

    def __init__(self, year=None, db_path: str = DB_PATH, *args, **kwargs) -> None:
        if year is None:
            year = strftime("%Y")

        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            pass

        self.year = str(year)
        self.db = Database(db_path)
        self.usdt_irt = get_usd_irt()

        # Fixed/known holdings, unrelated to the ledger itself
        self._usdt_amount = 0
        self._usd_amount = 51
        self._base_money = 3_000_437.6 + 5_750_000
        self._gold_amount = 1
        self.gold_irt = 18_000_000
        self.MONTH_NAMES = MONTH_NAMES

    # ------------------------------------------------------------------
    # Users (foreign-key target for transactions)
    # ------------------------------------------------------------------
    def add_user(self, name: str) -> int:
        """
        Add a new user (payment counterparty) if it doesn't already exist,
        and return its id either way. Names are matched case-insensitively
        after trimming whitespace, so "Mark Rob" and "mark rob" resolve to
        the same row instead of creating a duplicate.
        """
        name = " ".join(name.strip().split())
        if not name:
            raise ValueError("Name can't be empty")

        existing = self.db.conn.execute(
            "SELECT id FROM users WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if existing:
            return existing["id"]

        cursor = self.db.conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
        self.db.conn.commit()
        return cursor.lastrowid

    def get_users(self) -> list[tuple[int, str]]:
        rows = self.db.conn.execute("SELECT id, name FROM users ORDER BY name").fetchall()
        return [(row["id"], row["name"]) for row in rows]

    def rename_user(self, user_id: int, new_name: str) -> None:
        new_name = " ".join(new_name.strip().split())
        if not new_name:
            raise ValueError("Name can't be empty")
        self.db.conn.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, user_id))
        self.db.conn.commit()

    def delete_user(self, user_id: int) -> None:
        self.db.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.db.conn.commit()

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    def add_transaction(
        self,
        amount: float,
        is_income: bool,
        date: str,
        user_id: int | None = None,
        reason: str = "",
    ) -> int:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        cursor = self.db.conn.execute(
            """
            INSERT INTO transactions (amount, is_income, date, reason, user_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (amount, int(is_income), date, (reason or "").strip(), user_id),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def delete_transaction(self, transaction_id: int) -> None:
        self.db.conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.db.conn.commit()

    def get_transactions(self, year: str | None = None) -> list[sqlite3.Row]:
        """Transactions for a given year (defaults to self.year)."""
        year = year or self.year
        return self.db.conn.execute(
            """
            SELECT t.id, t.amount, t.is_income, t.date, t.reason,
                   u.name AS user_name
            FROM transactions t
            LEFT JOIN users u ON u.id = t.user_id
            WHERE t.date LIKE ?
            ORDER BY t.date DESC, t.id DESC
            """,
            (f"{year}%",),
        ).fetchall()

    def get_all_transactions(self) -> list[sqlite3.Row]:
        """Every transaction ever recorded, regardless of year."""
        return self.db.conn.execute(
            """
            SELECT t.id, t.amount, t.is_income, t.date, t.reason,
                   u.name AS user_name
            FROM transactions t
            LEFT JOIN users u ON u.id = t.user_id
            ORDER BY t.date DESC, t.id DESC
            """
        ).fetchall()

    # ------------------------------------------------------------------
    # Aggregates
    # ------------------------------------------------------------------
    def get_money_difference(self, year: str | None = None) -> float:
        year = year or self.year
        row = self.db.conn.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN is_income = 1 THEN amount ELSE -amount END), 0) AS total
            FROM transactions
            WHERE date LIKE ?
            """,
            (f"{year}%",),
        ).fetchone()
        return row["total"]

    def get_crypto_money(self) -> float:
        return self._usdt_amount * self.usdt_irt

    def get_dollars_money(self) -> float:
        return self._usd_amount * self.usdt_irt

    def get_gold_money(self) -> float:
        return self._gold_amount * self.gold_irt

    def get_money_before(self) -> float:
        return (
            self._base_money
            + self.get_crypto_money()
            + self.get_dollars_money()
            + self.get_gold_money()
        )

    def get_total_money(self) -> float:
        return self.get_money_before() + self.get_money_difference()

    def get_total_money_usdt(self) -> float:
        return round(self.get_total_money() / self.usdt_irt, 2)

    def get_usdt_irt(self) -> float:
        return self.usdt_irt

    def _get_monthly_money_differences(self, year: str | None = None) -> list[list]:
        """Per-month totals for the given year, in a single SQL query."""
        year = year or self.year
        rows = self.db.conn.execute(
            """
            SELECT substr(date, 6, 2) AS month,
                   COALESCE(SUM(CASE WHEN is_income = 1 THEN amount ELSE -amount END), 0) AS total
            FROM transactions
            WHERE date LIKE ?
            GROUP BY month
            ORDER BY month
            """,
            (f"{year}%",),
        ).fetchall()

        data = []
        for row in rows:
            try:
                month = int(row["month"])
            except (TypeError, ValueError):
                continue
            if row["total"]:
                data.append([month, row["total"]])
        return data

    def _get_monthly_table_data(self, year: str | None = None) -> list[tuple]:
        monthly_money_differences = self._get_monthly_money_differences(year)
        return [
            (
                self.MONTH_NAMES[month_index - 1],
                f"{total:,.0f} T",
                f"{total / self.usdt_irt:,.2f} $",
            )
            for month_index, total in monthly_money_differences
        ]

    def get_average_monthly_income(self, year: str | None = None) -> float:
        monthly_money_differences = self._get_monthly_money_differences(year)
        if not monthly_money_differences:
            return 0.0
        totals = [total for _, total in monthly_money_differences]
        return round(sum(totals) / len(totals), 2)

    # ------------------------------------------------------------------
    # Import: every format loads into a common list[dict] "records" shape,
    # then _insert_records() does the actual DB writing exactly once.
    # ------------------------------------------------------------------
    _RECORD_LOADERS = None  # populated at the bottom of the class body

    def import_ledger_file(self, file_path: str) -> dict:
        """
        Import a ledger/export file into the database. Supported
        extensions: .txt, .csv, .json, .toml, .yaml/.yml, .sql, .sqlite3/.db.
        Returns {"imported": int, "skipped": int, "errors": [str, ...]}.
        """
        ext = os.path.splitext(file_path)[1].lower()
        loader = self._RECORD_LOADERS.get(ext)
        if loader is None:
            return {
                "imported": 0,
                "skipped": 0,
                "errors": [f"Unsupported file type: '{ext or file_path}'"],
            }

        try:
            records, errors = loader(self, file_path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return {"imported": 0, "skipped": 0, "errors": [f"Couldn't read file: {exc}"]}

        return self._insert_records(records, errors)

    def _insert_records(self, records: list[dict], preexisting_errors: list[str] | None = None) -> dict:
        imported = 0
        skipped = 0
        errors = list(preexisting_errors or [])

        for index, record in enumerate(records, start=1):
            try:
                amount = float(record["amount"])
                is_income = bool(record["is_income"])
                iso_date = _normalize_date(str(record["date"]))
                person = (record.get("person") or "").strip() or None
                reason = record.get("reason") or ""

                user_id = self.add_user(person) if person else None
                self.add_transaction(amount, is_income, iso_date, user_id, reason)
                imported += 1
            except (KeyError, ValueError, TypeError) as exc:
                skipped += 1
                errors.append(f"Record {index}: {exc}")

        return {"imported": imported, "skipped": skipped, "errors": errors}

    def _load_txt_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        records, errors = [], []
        with open(file_path, encoding="utf-8") as file:
            for line_number, raw_line in enumerate(file, start=1):
                if not raw_line.strip():
                    continue
                record = parse_ledger_line(raw_line)
                if record is None:
                    errors.append(f"Line {line_number}: couldn't parse '{raw_line.strip()}'")
                    continue
                records.append(record)
        return records, errors

    def _load_csv_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        records, errors = [], []
        with open(file_path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            # Normalize header names so "amount"/"Amount"/"AMOUNT" all work.
            fieldmap = {name.strip().upper(): name for name in (reader.fieldnames or [])}
            required = {"TYPE", "AMOUNT", "DATE"}
            if not required.issubset(fieldmap):
                errors.append(
                    "CSV must contain columns: TYPE, AMOUNT, DATE, PERSON, REASON "
                    f"(found: {', '.join(reader.fieldnames or [])})"
                )
                return records, errors

            for row_number, row in enumerate(reader, start=2):  # header is row 1
                try:
                    type_value = row[fieldmap["TYPE"]].strip()
                    if type_value not in ("+", "-"):
                        raise ValueError(f"TYPE must be '+' or '-', got '{type_value}'")
                    records.append(
                        {
                            "amount": row[fieldmap["AMOUNT"]].strip().replace(",", ""),
                            "is_income": type_value == "+",
                            "date": row[fieldmap["DATE"]].strip(),
                            "person": row[fieldmap["PERSON"]].strip() if "PERSON" in fieldmap else "",
                            "reason": row[fieldmap["REASON"]].strip() if "REASON" in fieldmap else "",
                        }
                    )
                except (KeyError, ValueError) as exc:
                    errors.append(f"Row {row_number}: {exc}")
        return records, errors

    def _load_json_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)
        return self._records_from_generic(data), []

    def _load_toml_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # backport
            except ImportError as exc:
                raise RuntimeError(
                    "TOML import needs Python 3.11+, or run: pip install tomli"
                ) from exc

        with open(file_path, "rb") as file:
            data = tomllib.load(file)
        return self._records_from_generic(data.get("transactions", data)), []

    def _load_yaml_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "YAML import needs the 'PyYAML' package: pip install pyyaml"
            ) from exc

        with open(file_path, encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return self._records_from_generic(data), []

    def _load_sql_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        """Run a .sql script against a scratch in-memory DB, then read it back."""
        with open(file_path, encoding="utf-8") as file:
            script = file.read()

        scratch = sqlite3.connect(":memory:")
        try:
            scratch.executescript(script)
            return self._records_from_sqlite_conn(scratch), []
        finally:
            scratch.close()

    def _load_sqlite_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        """Read users/transactions straight out of another SQLite DB file."""
        source = sqlite3.connect(file_path)
        source.row_factory = sqlite3.Row
        try:
            return self._records_from_sqlite_conn(source), []
        finally:
            source.close()

    @staticmethod
    def _records_from_sqlite_conn(conn: sqlite3.Connection) -> list[dict]:
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT t.amount, t.is_income, t.date, t.reason, u.name AS person
                FROM transactions t
                LEFT JOIN users u ON u.id = t.user_id
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [
            {
                "amount": row["amount"],
                "is_income": bool(row["is_income"]),
                "date": row["date"],
                "person": row["person"],
                "reason": row["reason"],
            }
            for row in rows
        ]

    @staticmethod
    def _records_from_generic(data) -> list[dict]:
        """
        Normalize JSON/TOML/YAML data (as produced by this app's own
        export_json/export_toml/export_yaml) into the common record shape.
        Accepts either "+"/"-" or a boolean/int for the type field.
        """
        if isinstance(data, dict):
            data = data.get("transactions", [])
        if not isinstance(data, list):
            return []

        records = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            type_value = entry.get("type", entry.get("is_income"))
            if isinstance(type_value, str):
                is_income = type_value.strip() == "+"
            else:
                is_income = bool(type_value)
            records.append(
                {
                    "amount": entry.get("amount"),
                    "is_income": is_income,
                    "date": entry.get("date"),
                    "person": entry.get("person"),
                    "reason": entry.get("reason", ""),
                }
            )
        return records

    # ------------------------------------------------------------------
    # Export: json / csv / toml / yaml / sql / txt
    # ------------------------------------------------------------------
    def _export_rows(self, year: str | None = None) -> list[dict]:
        rows = self.get_transactions(year)
        return [
            {
                "type": "+" if row["is_income"] else "-",
                "amount": row["amount"],
                "date": row["date"],
                "person": row["user_name"] or "",
                "reason": row["reason"] or "",
            }
            for row in rows
        ]

    def export_json(self, path: str, year: str | None = None) -> int:
        data = self._export_rows(year)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        return len(data)

    def export_csv(self, path: str, year: str | None = None) -> int:
        data = self._export_rows(year)
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["TYPE", "AMOUNT", "DATE", "PERSON", "REASON"])
            writer.writeheader()
            for entry in data:
                writer.writerow(
                    {
                        "TYPE": entry["type"],
                        "AMOUNT": entry["amount"],
                        "DATE": entry["date"],
                        "PERSON": entry["person"],
                        "REASON": entry["reason"],
                    }
                )
        return len(data)

    def export_txt(self, path: str, year: str | None = None) -> int:
        """Export back into the original ledger-line format."""
        data = self._export_rows(year)
        with open(path, "w", encoding="utf-8") as file:
            for entry in data:
                date_slashes = entry["date"].replace("-", "/")
                amount_str = f"{entry['amount']:,.0f}"
                person = f" [{entry['person']}]" if entry["person"] else ""
                reason = f" [{entry['reason']}]" if entry["reason"] else ""
                file.write(f"{entry['type']} {amount_str} [{date_slashes}]{person}{reason}\n")
        return len(data)

    def export_toml(self, path: str, year: str | None = None) -> int:
        try:
            import tomli_w
        except ImportError as exc:
            raise RuntimeError(
                "TOML export needs the 'tomli_w' package: pip install tomli_w"
            ) from exc

        data = self._export_rows(year)
        with open(path, "wb") as file:
            tomli_w.dump({"transactions": data}, file)
        return len(data)

    def export_yaml(self, path: str, year: str | None = None) -> int:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "YAML export needs the 'PyYAML' package: pip install pyyaml"
            ) from exc

        data = self._export_rows(year)
        with open(path, "w", encoding="utf-8") as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)
        return len(data)

    def export_sql(self, path: str, year: str | None = None) -> int:
        """
        Export a full SQL dump (schema + data) of the users/transactions
        tables, usable to fully recreate the database elsewhere.
        """
        with open(path, "w", encoding="utf-8") as file:
            for line in self.db.conn.iterdump():
                file.write(f"{line}\n")
        row = self.db.conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()
        return row["n"]


# Map file extensions to their loader methods. Defined after the class body
# so the bound methods above already exist.
Economy._RECORD_LOADERS = {
    ".txt": Economy._load_txt_records,
    ".csv": Economy._load_csv_records,
    ".json": Economy._load_json_records,
    ".toml": Economy._load_toml_records,
    ".yaml": Economy._load_yaml_records,
    ".yml": Economy._load_yaml_records,
    ".sql": Economy._load_sql_records,
    ".sqlite3": Economy._load_sqlite_records,
    ".db": Economy._load_sqlite_records,
}


if __name__ == "__main__":
    economy = Economy()
    print(f"Year: {economy.year}")
    print("-" * 40)
    money_difference = economy.get_money_difference()
    sign = "+" if money_difference >= 0 else ""
    print(f"Money Difference: {sign} {money_difference:,.1f} T")
    print(f"Total Money: {economy.get_total_money():,.1f} T")
    print(f"Total Money USDT: {economy.get_total_money_usdt():,} $")
    print(f"1 USDT: {economy.get_usdt_irt():,.0f} T")