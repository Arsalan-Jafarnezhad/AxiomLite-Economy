"""
Payments tab: a sortable table listing every stored transaction, with
edit and delete support. Investment transfers (Asset column set) are
tinted differently so they read as "moved into an asset", not spending.

The edit dialog reuses the same field layout and validators as Add
Payment (see payment_form.py) so both forms behave identically.
"""

from tkinter import Frame, Label, StringVar, Toplevel, ttk, BOTH, LEFT, RIGHT, TOP, X, Y, YES, END
from tkinter import messagebox

from .payment_form import (
    ASSET_CHOICES,
    NO_ASSET,
    parse_amount,
    parse_asset,
    parse_date,
    resolve_user_id,
)
from .theme import ACCENT2, BG, FG, NEGATIVE, POSITIVE


class PaymentsTabMixin:
    """Mixin providing the Payments tab (full transaction table)."""

    def _build_payments_tab(self):
        container = Frame(self.payments_tab, bg=BG)
        container.pack(side=TOP, fill=BOTH, expand=YES, padx=40, pady=30)

        top_row = Frame(container, bg=BG)
        top_row.pack(side=TOP, fill=X, pady=(0, 12))
        ttk.Label(top_row, text="All Payments", style="Title.TLabel").pack(side=LEFT)
        ttk.Button(
            top_row, text="↻ Refresh", style="Ghost.TButton", command=self._refresh_payments_tree
        ).pack(side=RIGHT)
        ttk.Button(
            top_row, text="🗑 Delete Selected", style="Danger.TButton",
            command=self._on_delete_payment_click,
        ).pack(side=RIGHT, padx=(0, 8))
        ttk.Button(
            top_row, text="✏️ Edit Selected", style="Ghost.TButton",
            command=self._on_edit_payment_click,
        ).pack(side=RIGHT, padx=(0, 8))

        columns = ("id", "date", "type", "amount", "person", "asset", "qty", "reason")
        self.payments_tree = ttk.Treeview(container, columns=columns, show="headings", height=18)
        headings = {
            "id": ("ID", 40), "date": ("Date", 100), "type": ("Type", 55),
            "amount": ("Amount (T)", 120), "person": ("Person", 140),
            "asset": ("Asset", 70), "qty": ("Qty", 90), "reason": ("Reason", 220),
        }
        for key, (label, width) in headings.items():
            self.payments_tree.heading(key, text=label)
            anchor = "center" if key in ("id", "type", "asset", "qty") else "w"
            self.payments_tree.column(key, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.payments_tree.yview)
        self.payments_tree.configure(yscrollcommand=scrollbar.set)
        self.payments_tree.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.payments_tree.tag_configure("income", foreground=POSITIVE)
        self.payments_tree.tag_configure("expense", foreground=NEGATIVE)
        self.payments_tree.tag_configure("asset", foreground=ACCENT2)
        self.payments_tree.bind("<Double-1>", lambda _e: self._on_edit_payment_click())
        self._make_sortable(self.payments_tree, numeric_columns={"id", "amount", "qty"})

    def _refresh_payments_tree(self):
        self.payments_tree.delete(*self.payments_tree.get_children())
        for row in self.get_all_transactions():
            sign = "+" if row["is_income"] else "-"
            is_asset = bool(row["asset_type"])
            tag = "asset" if is_asset else ("income" if row["is_income"] else "expense")
            qty = f"{row['asset_quantity']:,.4g}" if row["asset_quantity"] is not None else "-"
            self.payments_tree.insert(
                "", END,
                values=(
                    row["id"], row["date"], sign, f"{row['amount']:,.0f}",
                    row["user_name"] or "-", row["asset_type"] or "-", qty,
                    row["reason"] or "-",
                ),
                tags=(tag,),
            )

    def _selected_transaction_id(self) -> int | None:
        selection = self.payments_tree.selection()
        if not selection:
            messagebox.showwarning("Nothing selected", "Select a payment first.")
            return None
        return self.payments_tree.item(selection[0])["values"][0]

    def _on_delete_payment_click(self):
        transaction_id = self._selected_transaction_id()
        if transaction_id is None:
            return
        if messagebox.askyesno("Delete payment", f"Delete payment #{transaction_id}? This can't be undone."):
            self.delete_transaction(transaction_id)
            self.refresh_all()

    def _on_edit_payment_click(self):
        transaction_id = self._selected_transaction_id()
        if transaction_id is None:
            return
        transaction = self.get_transaction(transaction_id)
        if transaction is None:
            messagebox.showerror("Not found", "That payment no longer exists.")
            self.refresh_all()
            return
        self._open_edit_payment_dialog(transaction)

    # ------------------------------------------------------------------
    # Edit dialog - same fields/validators as Add Payment, pre-filled
    # ------------------------------------------------------------------
    def _open_edit_payment_dialog(self, transaction):
        dialog = Toplevel(self.master)
        dialog.title(f"Edit Payment #{transaction['id']}")
        dialog.configure(bg=BG)
        dialog.geometry("380x420")
        dialog.transient(self.master)
        dialog.grab_set()

        form = Frame(dialog, bg=BG)
        form.pack(fill=BOTH, expand=YES, padx=20, pady=20)

        def field_label(text, row):
            Label(form, text=text, bg=BG, fg=FG, font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="w", pady=6
            )

        field_label("Amount (T)", 0)
        amount_var = StringVar(value=f"{transaction['amount']:g}")
        ttk.Entry(form, textvariable=amount_var, width=26).grid(row=0, column=1, sticky="w", pady=6)

        field_label("Type", 1)
        type_var = StringVar(value="income" if transaction["is_income"] else "expense")
        type_frame = Frame(form, bg=BG)
        type_frame.grid(row=1, column=1, sticky="w", pady=6)
        ttk.Radiobutton(type_frame, text="Income (+)", variable=type_var, value="income").pack(side=LEFT)
        ttk.Radiobutton(type_frame, text="Expense (-)", variable=type_var, value="expense").pack(
            side=LEFT, padx=(10, 0)
        )

        field_label("Date (YYYY-MM-DD)", 2)
        date_var = StringVar(value=transaction["date"])
        ttk.Entry(form, textvariable=date_var, width=26).grid(row=2, column=1, sticky="w", pady=6)

        field_label("Person", 3)
        user_lookup = {name: user_id for user_id, name in self.get_users()}
        user_var = StringVar(value=transaction["user_name"] or "")
        user_combo = ttk.Combobox(
            form, textvariable=user_var, width=24, state="readonly",
            values=list(user_lookup.keys()) or [""],
        )
        user_combo.grid(row=3, column=1, sticky="w", pady=6)

        field_label("Reason", 4)
        reason_var = StringVar(value=transaction["reason"] or "")
        ttk.Entry(form, textvariable=reason_var, width=26).grid(row=4, column=1, sticky="w", pady=6)

        field_label("Asset", 5)
        asset_var = StringVar(value=transaction["asset_type"] or NO_ASSET)
        asset_combo = ttk.Combobox(
            form, textvariable=asset_var, width=24, state="readonly", values=ASSET_CHOICES
        )
        asset_combo.grid(row=5, column=1, sticky="w", pady=6)

        field_label("Quantity", 6)
        quantity_var = StringVar(
            value=f"{transaction['asset_quantity']:g}" if transaction["asset_quantity"] is not None else ""
        )
        quantity_entry = ttk.Entry(form, textvariable=quantity_var, width=26)
        quantity_entry.grid(row=6, column=1, sticky="w", pady=6)
        quantity_entry.configure(state="normal" if transaction["asset_type"] else "disabled")

        def on_asset_change(_event=None):
            enabled = asset_var.get() != NO_ASSET
            quantity_entry.configure(state="normal" if enabled else "disabled")
            if not enabled:
                quantity_var.set("")

        asset_combo.bind("<<ComboboxSelected>>", on_asset_change)

        def save_and_close():
            try:
                amount = parse_amount(amount_var.get())
                date_text = parse_date(date_var.get())
                asset_type, asset_quantity = parse_asset(asset_var.get(), quantity_var.get())
            except ValueError as exc:
                messagebox.showerror("Invalid input", str(exc), parent=dialog)
                return

            user_id = resolve_user_id(user_var.get(), user_lookup)
            is_income = type_var.get() == "income"
            reason = reason_var.get().strip()

            try:
                self.update_transaction(
                    transaction["id"], amount, is_income, date_text, user_id, reason,
                    asset_type=asset_type, asset_quantity=asset_quantity,
                )
            except ValueError as exc:
                messagebox.showerror("Couldn't save payment", str(exc), parent=dialog)
                return

            dialog.destroy()
            self.refresh_all()

        button_row = Frame(form, bg=BG)
        button_row.grid(row=7, column=0, columnspan=2, pady=(20, 0), sticky="w")
        ttk.Button(button_row, text="💾 Save", style="Accent.TButton", command=save_and_close).pack(
            side=LEFT, padx=(0, 8)
        )
        ttk.Button(button_row, text="Cancel", style="Ghost.TButton", command=dialog.destroy).pack(side=LEFT)
        dialog.bind("<Return>", lambda _e: save_and_close())
