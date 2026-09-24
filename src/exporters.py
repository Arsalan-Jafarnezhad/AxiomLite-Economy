"""
Export pipeline: json / csv / txt / toml / yaml / sql.
"""

import csv
import json


class ExportMixin:
    """
    Mixin providing every export_* method. Expects to be combined with
    EconomyCore (for get_transactions/db.conn).
    """

    def _export_rows(self, year: str | None = None) -> list[dict]:
        rows = self.get_transactions(year)
        return [
            {
                "type": "+" if row["is_income"] else "-",
                "amount": row["amount"],
                "date": row["date"],
                "person": row["user_name"] or "",
                "reason": row["reason"] or "",
                "asset_type": row["asset_type"],
                "asset_quantity": row["asset_quantity"],
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
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "TYPE",
                    "AMOUNT",
                    "DATE",
                    "PERSON",
                    "REASON",
                    "ASSET",
                    "QTY",
                ],
            )
            writer.writeheader()
            for entry in data:
                writer.writerow(
                    {
                        "TYPE": entry["type"],
                        "AMOUNT": entry["amount"],
                        "DATE": entry["date"],
                        "PERSON": entry["person"],
                        "REASON": entry["reason"],
                        "ASSET": entry["asset_type"] or "",
                        "QTY": (
                            entry["asset_quantity"]
                            if entry["asset_quantity"] is not None
                            else ""
                        ),
                    }
                )
        return len(data)

    def export_txt(self, path: str, year: str | None = None) -> int:
        """
        Export back into the ledger-line format. An asset transaction's
        reason is written as "<ASSET> QTY <quantity>" (overriding
        whatever reason it was entered with) so a round-trip import
        recovers the exact quantity instead of re-deriving it from a
        price note.
        """
        data = self._export_rows(year)
        with open(path, "w", encoding="utf-8") as file:
            for entry in data:
                date_slashes = entry["date"].replace("-", "/")
                amount_str = f"{entry['amount']:,.0f}"
                # Always emit the person bracket, even empty - the ledger
                # format is positional (date, person, reason), so omitting
                # it when there's no person would shift the reason into
                # the person slot on re-import.
                person = f" [{entry['person']}]"

                if entry["asset_type"] and entry["asset_quantity"] is not None:
                    # Use :f format to avoid scientific notation for large numbers
                    # which would break round-trip import (ledger.py regex doesn't match e.g. 1.23e+06)
                    reason_text = (
                        f"{entry['asset_type']} QTY {entry['asset_quantity']:f}"
                    )
                else:
                    reason_text = entry["reason"]
                reason = f" [{reason_text}]" if reason_text else ""

                file.write(
                    f"{entry['type']} {amount_str} [{date_slashes}]{person}{reason}\n"
                )
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

    def export_sql(self, path: str) -> int:
        """
        Export a full SQL dump (schema + data) of the users/transactions
        tables, usable to fully recreate the database elsewhere.
        Unlike the other export formats, this always exports the complete
        database (all years), including the schema.
        """
        with open(path, "w", encoding="utf-8") as file:
            for line in self.db.conn.iterdump():
                file.write(f"{line}\n")
        row = self.db.conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()
        return row["n"]
