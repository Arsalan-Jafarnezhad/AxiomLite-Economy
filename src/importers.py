"""
Import pipeline.

Every supported file format (.txt, .csv, .json, .toml, .yaml/.yml, .sql,
.sqlite3/.db) is normalized by a small loader into a common list[dict]
"records" shape - {"amount", "is_income", "date", "person", "reason",
"asset_type", "asset_quantity"} - and then funneled through
_insert_records(), which is the only place that actually writes to the
database. asset_type/asset_quantity are None for ordinary transactions;
see ledger.parse_asset_shorthand() for how a plain-text "GOLD <price>"
/ "USDT <price>" reason gets turned into them automatically.
"""

import csv
import json
import os
import sqlite3

from .ledger import normalize_date, parse_asset_shorthand, parse_ledger_line


class ImportMixin:
    """
    Mixin providing import_ledger_file() and its format loaders. Expects
    to be combined with EconomyCore (for add_user/add_transaction).
    """

    _RECORD_LOADERS: dict | None = None  # populated at the bottom of this module

    def import_ledger_file(self, file_path: str) -> dict:
        """
        Import a file into the database. Returns
        {"imported": int, "skipped": int, "errors": [str, ...]}.
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
        except (OSError, UnicodeDecodeError, ValueError, sqlite3.Error) as exc:
            return {
                "imported": 0,
                "skipped": 0,
                "errors": [f"Couldn't read file: {exc}"],
            }

        return self._insert_records(records, errors)

    def _insert_records(
        self, records: list[dict], preexisting_errors: list[str] | None = None
    ) -> dict:
        imported = 0
        skipped = 0
        errors = list(preexisting_errors or [])

        for index, record in enumerate(records, start=1):
            try:
                amount = float(record["amount"])
                is_income = bool(record["is_income"])
                iso_date = normalize_date(str(record["date"]))
                person = (record.get("person") or "").strip() or None
                reason = record.get("reason") or ""
                asset_type = record.get("asset_type") or None
                asset_quantity = record.get("asset_quantity")

                # Plain-text shorthand fallback: a reason like "GOLD 14000000"
                # implies an asset transaction even if no explicit asset_type
                # column was provided (older exports, hand-written CSVs, ...).
                if asset_type is None:
                    shorthand = parse_asset_shorthand(reason, amount)
                    if shorthand:
                        asset_type, asset_quantity = shorthand

                # Use a transaction to ensure atomicity: either both user and transaction are created,
                # or neither is created. This prevents orphaned users if the transaction fails.
                self.db.conn.execute("BEGIN")
                try:
                    user_id = self.add_user(person) if person else None
                    self.add_transaction(
                        amount,
                        is_income,
                        iso_date,
                        user_id,
                        reason,
                        asset_type=asset_type,
                        asset_quantity=asset_quantity,
                    )
                    self.db.conn.commit()
                    imported += 1
                except Exception:
                    self.db.conn.rollback()
                    raise
            except (KeyError, ValueError, TypeError) as exc:
                skipped += 1
                errors.append(f"Record {index}: {exc}")

        return {"imported": imported, "skipped": skipped, "errors": errors}

    # ------------------------------------------------------------------
    # Per-format loaders: each returns (records, errors)
    # ------------------------------------------------------------------
    def _load_txt_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        records, errors = [], []
        with open(file_path, encoding="utf-8") as file:
            for line_number, raw_line in enumerate(file, start=1):
                if not raw_line.strip():
                    continue
                record = parse_ledger_line(raw_line)
                if record is None:
                    errors.append(
                        f"Line {line_number}: couldn't parse '{raw_line.strip()}'"
                    )
                    continue
                records.append(record)
        return records, errors

    def _load_csv_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        records, errors = [], []
        with open(file_path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            # Normalize header names so "amount"/"Amount"/"AMOUNT" all work.
            fieldmap = {
                name.strip().upper(): name for name in (reader.fieldnames or [])
            }
            required = {"TYPE", "AMOUNT", "DATE"}
            if not required.issubset(fieldmap):
                errors.append(
                    "CSV must contain columns: TYPE, AMOUNT, DATE, PERSON, REASON "
                    "(optionally ASSET, QTY) "
                    f"(found: {', '.join(reader.fieldnames or [])})"
                )
                return records, errors

            for row_number, row in enumerate(reader, start=2):  # header is row 1
                try:
                    type_value = row[fieldmap["TYPE"]].strip()
                    if type_value not in ("+", "-"):
                        raise ValueError(f"TYPE must be '+' or '-', got '{type_value}'")

                    asset_type = (
                        row[fieldmap["ASSET"]].strip() if "ASSET" in fieldmap else ""
                    )
                    qty_text = row[fieldmap["QTY"]].strip() if "QTY" in fieldmap else ""

                    records.append(
                        {
                            "amount": row[fieldmap["AMOUNT"]].strip().replace(",", ""),
                            "is_income": type_value == "+",
                            "date": row[fieldmap["DATE"]].strip(),
                            "person": (
                                row[fieldmap["PERSON"]].strip()
                                if "PERSON" in fieldmap
                                else ""
                            ),
                            "reason": (
                                row[fieldmap["REASON"]].strip()
                                if "REASON" in fieldmap
                                else ""
                            ),
                            "asset_type": asset_type or None,
                            "asset_quantity": (
                                float(qty_text.replace(",", "")) if qty_text else None
                            ),
                        }
                    )
                except (KeyError, ValueError) as exc:
                    errors.append(f"Row {row_number}: {exc}")
        return records, errors

    def _load_json_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)
        return _records_from_generic(data), []

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
        return _records_from_generic(data.get("transactions", data)), []

    def _load_yaml_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "YAML import needs the 'PyYAML' package: pip install pyyaml"
            ) from exc

        with open(file_path, encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return _records_from_generic(data), []

    def _load_sql_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        """Run a .sql script against a scratch in-memory DB, then read it back."""
        with open(file_path, encoding="utf-8") as file:
            script = file.read()

        scratch = sqlite3.connect(":memory:")
        try:
            scratch.executescript(script)
            return _records_from_sqlite_conn(scratch), []
        finally:
            scratch.close()

    def _load_sqlite_records(self, file_path: str) -> tuple[list[dict], list[str]]:
        """Read users/transactions straight out of another SQLite DB file."""
        source = sqlite3.connect(file_path)
        source.row_factory = sqlite3.Row
        try:
            return _records_from_sqlite_conn(source), []
        finally:
            source.close()


def _records_from_sqlite_conn(conn: sqlite3.Connection) -> list[dict]:
    """
    Read transactions from another Axiom Economy database. Tries the
    current schema (with asset columns) first, and falls back to the
    pre-asset-tracking schema for dumps made by an older version.
    """
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT t.amount, t.is_income, t.date, t.reason,
                   t.asset_type, t.asset_quantity, u.name AS person
            FROM transactions t
            LEFT JOIN users u ON u.id = t.user_id
            """).fetchall()
        has_asset_columns = True
    except sqlite3.OperationalError:
        try:
            rows = conn.execute("""
                SELECT t.amount, t.is_income, t.date, t.reason, u.name AS person
                FROM transactions t
                LEFT JOIN users u ON u.id = t.user_id
                """).fetchall()
            has_asset_columns = False
        except sqlite3.OperationalError:
            return []

    return [
        {
            "amount": row["amount"],
            "is_income": bool(row["is_income"]),
            "date": row["date"],
            "person": row["person"],
            "reason": row["reason"],
            "asset_type": row["asset_type"] if has_asset_columns else None,
            "asset_quantity": row["asset_quantity"] if has_asset_columns else None,
        }
        for row in rows
    ]


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
                "asset_type": entry.get("asset_type") or None,
                "asset_quantity": entry.get("asset_quantity"),
            }
        )
    return records


# Map file extensions to their loader methods. Defined after the class body
# so the bound methods above already exist.
ImportMixin._RECORD_LOADERS = {
    ".txt": ImportMixin._load_txt_records,
    ".csv": ImportMixin._load_csv_records,
    ".json": ImportMixin._load_json_records,
    ".toml": ImportMixin._load_toml_records,
    ".yaml": ImportMixin._load_yaml_records,
    ".yml": ImportMixin._load_yaml_records,
    ".sql": ImportMixin._load_sql_records,
    ".sqlite3": ImportMixin._load_sqlite_records,
    ".db": ImportMixin._load_sqlite_records,
}
