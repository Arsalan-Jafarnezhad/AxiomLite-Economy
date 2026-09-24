"""
Core Economy logic: user/transaction CRUD and aggregate calculations.
Import and export behavior live in importers.py / exporters.py so each
file stays focused on one concern.

Investment transactions (buying/selling USDT or GOLD, marked by
asset_type/asset_quantity) are cash <-> asset transfers, not spending,
so cash-flow aggregates (get_money_difference, the monthly breakdown)
exclude them; your USDT/GOLD holdings are instead derived from the sum
of those same transactions in get_asset_holdings().
"""

import sqlite3
from pathlib import Path
from time import strftime

from .config import DB_PATH
from .db import Database
from .price import get_gold_irt, get_usd_irt

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

ASSET_TYPES = ("USDT", "GOLD")


class EconomyCore:
    """Personal economy / money tracking, backed by SQLite."""

    def __init__(
        self, year=None, db_path: Path | str = DB_PATH, *args, **kwargs
    ) -> None:
        if year is None:
            year = strftime("%Y")

        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            pass

        self.year = str(year)
        self.db = Database(db_path)
        self.usdt_irt = get_usd_irt()

        # Fixed/known values, unrelated to the transaction ledger itself.
        # USDT and GOLD holdings are NOT listed here - they're computed
        # dynamically from investment transactions, see get_asset_holdings().
        self._base_usd_amount = 51
        self._base_usdt_amount = 32.35
        self._base_money = 3_000_437.6 + 5_750_000
        self.gold_irt = get_gold_irt()  # price per gram, used to value gold holdings
        self.MONTH_NAMES = MONTH_NAMES

    # ------------------------------------------------------------------
    # Users (foreign-key target for transactions)
    # ------------------------------------------------------------------
    def add_user(self, name: str, commit: bool = True) -> int:
        """
        Add a new user (payment counterparty) if it doesn't already exist,
        and return its id either way. Names are matched case-insensitively
        after trimming whitespace, so "Mark Rob" and "mark rob" resolve to
        the same row instead of creating a duplicate.

        Args:
            name: The user's name
            commit: Whether to commit the transaction immediately. Defaults to True.
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
        if commit:
            self.db.conn.commit()
        return cursor.lastrowid

    def get_users(self) -> list[tuple[int, str]]:
        rows = self.db.conn.execute(
            "SELECT id, name FROM users ORDER BY name"
        ).fetchall()
        return [(row["id"], row["name"]) for row in rows]

    def rename_user(self, user_id: int, new_name: str) -> None:
        new_name = " ".join(new_name.strip().split())
        if not new_name:
            raise ValueError("Name can't be empty")
        self.db.conn.execute(
            "UPDATE users SET name = ? WHERE id = ?", (new_name, user_id)
        )
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
        asset_type: str | None = None,
        asset_quantity: float | None = None,
        commit: bool = True,
    ) -> int:
        """
        `asset_type` ("USDT"/"GOLD") + `asset_quantity` mark this as an
        investment transfer: is_income=False means buying that quantity
        of the asset with `amount` T; is_income=True means selling it
        back for `amount` T. Leave both None for an ordinary transaction.

        Args:
            amount: The transaction amount
            is_income: Whether this is income
            date: Transaction date
            user_id: Optional user id
            reason: Optional reason
            asset_type: Optional asset type
            asset_quantity: Optional asset quantity
            commit: Whether to commit the transaction immediately. Defaults to True.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if asset_type is not None:
            asset_type = asset_type.strip().upper()
            if asset_type not in ASSET_TYPES:
                raise ValueError(
                    f"asset_type must be one of {ASSET_TYPES}, got '{asset_type}'"
                )
            if not asset_quantity or asset_quantity <= 0:
                raise ValueError(
                    "asset_quantity must be a positive number for an asset transaction"
                )

        cursor = self.db.conn.execute(
            """
            INSERT INTO transactions (amount, is_income, date, reason, user_id, asset_type, asset_quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                amount,
                int(is_income),
                date,
                (reason or "").strip(),
                user_id,
                asset_type,
                asset_quantity,
            ),
        )
        if commit:
            self.db.conn.commit()
        return cursor.lastrowid

    def update_transaction(
        self,
        transaction_id: int,
        amount: float,
        is_income: bool,
        date: str,
        user_id: int | None = None,
        reason: str = "",
        asset_type: str | None = None,
        asset_quantity: float | None = None,
    ) -> None:
        """Overwrite every editable field of an existing transaction."""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if asset_type is not None:
            asset_type = asset_type.strip().upper()
            if asset_type not in ASSET_TYPES:
                raise ValueError(
                    f"asset_type must be one of {ASSET_TYPES}, got '{asset_type}'"
                )
            if not asset_quantity or asset_quantity <= 0:
                raise ValueError(
                    "asset_quantity must be a positive number for an asset transaction"
                )

        self.db.conn.execute(
            """
            UPDATE transactions
            SET amount = ?, is_income = ?, date = ?, reason = ?, user_id = ?,
                asset_type = ?, asset_quantity = ?
            WHERE id = ?
            """,
            (
                amount,
                int(is_income),
                date,
                (reason or "").strip(),
                user_id,
                asset_type,
                asset_quantity,
                transaction_id,
            ),
        )
        self.db.conn.commit()

    def delete_transaction(self, transaction_id: int) -> None:
        self.db.conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.db.conn.commit()

    def get_transactions(self, year: str | None = None) -> list[sqlite3.Row]:
        """Transactions for a given year (defaults to self.year)."""
        year = year or self.year
        return self.db.conn.execute(
            """
            SELECT t.id, t.amount, t.is_income, t.date, t.reason,
                   t.asset_type, t.asset_quantity, u.name AS user_name
            FROM transactions t
            LEFT JOIN users u ON u.id = t.user_id
            WHERE t.date LIKE ?
            ORDER BY t.date DESC, t.id DESC
            """,
            (f"{year}%",),
        ).fetchall()

    def get_transaction(self, transaction_id: int) -> sqlite3.Row | None:
        """A single transaction by id, including its raw user_id (for edit forms)."""
        return self.db.conn.execute(
            """
            SELECT t.id, t.amount, t.is_income, t.date, t.reason, t.user_id,
                   t.asset_type, t.asset_quantity, u.name AS user_name
            FROM transactions t
            LEFT JOIN users u ON u.id = t.user_id
            WHERE t.id = ?
            """,
            (transaction_id,),
        ).fetchone()

    def get_all_transactions(self) -> list[sqlite3.Row]:
        """Every transaction ever recorded, regardless of year."""
        return self.db.conn.execute("""
            SELECT t.id, t.amount, t.is_income, t.date, t.reason,
                   t.asset_type, t.asset_quantity, u.name AS user_name
            FROM transactions t
            LEFT JOIN users u ON u.id = t.user_id
            ORDER BY t.date DESC, t.id DESC
            """).fetchall()

    # ------------------------------------------------------------------
    # Aggregates (cash flow - excludes investment transfers)
    # ------------------------------------------------------------------
    def get_money_difference(self, year: str | None = None) -> float:
        year = year or self.year
        row = self.db.conn.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN is_income = 1 THEN amount ELSE -amount END), 0) AS total
            FROM transactions
            WHERE date LIKE ? AND asset_type IS NULL
            """,
            (f"{year}%",),
        ).fetchone()
        return row["total"]

    def get_asset_holdings(self, asset_type: str) -> float:
        """
        Net quantity of `asset_type` ("USDT"/"GOLD") currently held,
        summed across every buy/sell transaction ever recorded (not
        limited to the current year - holdings persist across years).
        """
        asset_type = asset_type.strip().upper()
        row = self.db.conn.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN is_income = 1 THEN -asset_quantity ELSE asset_quantity END), 0) AS total
            FROM transactions
            WHERE asset_type = ?
            """,
            (asset_type,),
        ).fetchone()
        return row["total"]

    def get_crypto_money(self) -> float:
        return self.get_asset_holdings("USDT") * self.usdt_irt

    def get_dollars_money(self) -> float:
        return (self._base_usd_amount + self._base_usdt_amount) * self.usdt_irt

    def get_gold_money(self) -> float:
        return self.get_asset_holdings("GOLD") * self.gold_irt

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
        """Per-month cash-flow totals for the given year (excludes investment transfers)."""
        year = year or self.year
        rows = self.db.conn.execute(
            """
            SELECT substr(date, 6, 2) AS month,
                   COALESCE(SUM(CASE WHEN is_income = 1 THEN amount ELSE -amount END), 0) AS total
            FROM transactions
            WHERE date LIKE ? AND asset_type IS NULL
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
            if not 1 <= month <= 12:
                continue
            if row["total"] is not None:
                data.append([month, row["total"]])
        return data

    def _get_monthly_asset_totals(
        self, asset_type: str, year: str | None = None
    ) -> list[list]:
        """
        Per-month current IRT value of `asset_type` bought/sold that
        month (net quantity that month * today's live price), for the
        dashboard's "show investments" chart overlay. A buy contributes
        a positive value (money moved into the asset that month); a
        sell contributes negative (money moved back to cash).
        """
        asset_type = asset_type.strip().upper()
        year = year or self.year
        price = self.usdt_irt if asset_type == "USDT" else self.gold_irt

        rows = self.db.conn.execute(
            """
            SELECT substr(date, 6, 2) AS month,
                   COALESCE(SUM(CASE WHEN is_income = 1 THEN -asset_quantity ELSE asset_quantity END), 0) AS qty
            FROM transactions
            WHERE date LIKE ? AND asset_type = ?
            GROUP BY month
            ORDER BY month
            """,
            (f"{year}%", asset_type),
        ).fetchall()

        data = []
        for row in rows:
            try:
                month = int(row["month"])
            except (TypeError, ValueError):
                continue
            if row["qty"]:
                data.append([month, row["qty"] * price])
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
