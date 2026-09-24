"""
Add Payment tab: amount/type/date/person/reason form, plus an optional
Asset + Quantity pair for recording a USDT/GOLD buy or sell. The
"person" combobox is read-only and backed by the users table (foreign
key), with a "+ Add new user..." entry that opens a small dialog
instead of letting someone free-type a name and risk a typo'd
duplicate.

Marking a transaction with an asset makes it an investment transfer
(see core.EconomyCore): Expense = buying that quantity of the asset
with the amount paid; Income = selling it back for the amount received.
Such transactions are excluded from the spending dashboard by default
(see dashboard_tab's "Show USDT/GOLD" filters) and instead feed your
USDT/GOLD holdings automatically.

Validation logic lives in payment_form.py, shared with the Payments-tab
edit dialog so both forms behave identically.
"""

from tkinter import Frame, Label, StringVar, Toplevel, ttk, END, LEFT
from tkinter import messagebox

from .payment_form import (
    ASSET_CHOICES,
    NEW_USER_SENTINEL,
    NO_ASSET,
    parse_amount,
    parse_asset,
    parse_date,
    resolve_user_id,
)
from .theme import BG, FG

from datetime import date


class AddPaymentTabMixin:
    """Mixin providing the Add Payment tab and its user-select dialog."""

    def _build_add_payment_tab(self):
        form = Frame(self.add_payment_tab, bg=BG)
        form.pack(side="top", fill="x", padx=40, pady=30)

        ttk.Label(form, text="Add a New Payment", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 20)
        )

        ttk.Label(form, text="Amount (T)", style="Field.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        self.amount_var = StringVar()
        ttk.Entry(form, textvariable=self.amount_var, width=30).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Type", style="Field.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        self.type_var = StringVar(value="expense")
        type_frame = Frame(form, bg=BG)
        type_frame.grid(row=2, column=1, sticky="w", pady=6)
        ttk.Radiobutton(type_frame, text="Income (+)", variable=self.type_var, value="income").pack(side=LEFT)
        ttk.Radiobutton(type_frame, text="Expense (-)", variable=self.type_var, value="expense").pack(
            side=LEFT, padx=(16, 0)
        )

        ttk.Label(form, text="Date (YYYY-MM-DD)", style="Field.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        self.date_var = StringVar(value=date.today().isoformat())
        ttk.Entry(form, textvariable=self.date_var, width=30).grid(row=3, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Person", style="Field.TLabel").grid(row=4, column=0, sticky="w", pady=6)
        self.user_var = StringVar()
        self.user_combo = ttk.Combobox(form, textvariable=self.user_var, width=28, state="readonly")
        self.user_combo.grid(row=4, column=1, sticky="w", pady=6)
        self.user_combo.bind("<<ComboboxSelected>>", self._on_user_combo_change)

        ttk.Label(form, text="Reason", style="Field.TLabel").grid(row=5, column=0, sticky="w", pady=6)
        self.reason_var = StringVar()
        ttk.Entry(form, textvariable=self.reason_var, width=30).grid(row=5, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Asset", style="Field.TLabel").grid(row=6, column=0, sticky="w", pady=6)
        self.asset_var = StringVar(value=NO_ASSET)
        self.asset_combo = ttk.Combobox(
            form, textvariable=self.asset_var, width=28, state="readonly", values=ASSET_CHOICES
        )
        self.asset_combo.grid(row=6, column=1, sticky="w", pady=6)
        self.asset_combo.bind("<<ComboboxSelected>>", self._on_asset_combo_change)

        self.quantity_label = ttk.Label(
            form, text="Quantity (USDT / grams)", style="Field.TLabel"
        )
        self.quantity_label.grid(row=7, column=0, sticky="w", pady=6)
        self.quantity_var = StringVar()
        self.quantity_entry = ttk.Entry(form, textvariable=self.quantity_var, width=30)
        self.quantity_entry.grid(row=7, column=1, sticky="w", pady=6)
        self._set_quantity_field_enabled(False)

        ttk.Label(
            form,
            text=(
                "Marking Asset excludes this payment from the spending dashboard by\n"
                "default - it's treated as an investment transfer, not an expense."
            ),
            style="Subtitle.TLabel",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Button(
            form, text="💾  Save Payment", style="Accent.TButton", command=self._on_save_payment
        ).grid(row=9, column=1, sticky="w", pady=(20, 0))

    def _set_quantity_field_enabled(self, enabled: bool):
        self.quantity_entry.configure(state="normal" if enabled else "disabled")
        if not enabled:
            self.quantity_var.set("")

    def _on_asset_combo_change(self, _event=None):
        self._set_quantity_field_enabled(self.asset_var.get() != NO_ASSET)

    def _refresh_user_combo(self, keep_selection: str | None = None):
        self._user_lookup = {name: user_id for user_id, name in self.get_users()}
        values = list(self._user_lookup.keys()) + [NEW_USER_SENTINEL]
        self.user_combo["values"] = values
        if keep_selection and keep_selection in self._user_lookup:
            self.user_var.set(keep_selection)
        elif values:
            self.user_var.set(values[0])

    def _on_user_combo_change(self, _event=None):
        if self.user_var.get() == NEW_USER_SENTINEL:
            self._open_add_user_dialog(on_created=self._refresh_user_combo)

    def _on_save_payment(self):
        try:
            amount = parse_amount(self.amount_var.get())
            date_text = parse_date(self.date_var.get())
            asset_type, asset_quantity = parse_asset(self.asset_var.get(), self.quantity_var.get())
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        user_id = resolve_user_id(self.user_var.get(), self._user_lookup)
        is_income = self.type_var.get() == "income"
        reason = self.reason_var.get().strip()

        try:
            self.add_transaction(
                amount, is_income, date_text, user_id, reason,
                asset_type=asset_type, asset_quantity=asset_quantity,
            )
        except ValueError as exc:
            messagebox.showerror("Couldn't save payment", str(exc))
            return

        messagebox.showinfo("Saved", "Payment saved successfully.")
        self.amount_var.set("")
        self.reason_var.set("")
        self.asset_var.set(NO_ASSET)
        self._set_quantity_field_enabled(False)
        self.refresh_all()

    def _open_add_user_dialog(self, on_created=None):
        dialog = Toplevel(self.master)
        dialog.title("Add New User")
        dialog.configure(bg=BG)
        dialog.geometry("320x150")
        dialog.transient(self.master)
        dialog.grab_set()

        Label(dialog, text="New user's name", bg=BG, fg=FG, font=("Segoe UI", 11)).pack(pady=(20, 8))
        name_var = StringVar()
        entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        entry.pack()
        entry.focus_set()

        def save_and_close():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Missing name", "Please type a name.", parent=dialog)
                return
            try:
                self.add_user(name)
            except ValueError as exc:
                messagebox.showerror("Couldn't add user", str(exc), parent=dialog)
                return
            self._refresh_users_tree()
            if on_created:
                on_created(keep_selection=name)
            dialog.destroy()

        button_row = Frame(dialog, bg=BG)
        button_row.pack(pady=16)
        ttk.Button(button_row, text="Save", style="Accent.TButton", command=save_and_close).pack(side=LEFT, padx=6)
        ttk.Button(button_row, text="Cancel", style="Ghost.TButton", command=dialog.destroy).pack(side=LEFT, padx=6)
        dialog.bind("<Return>", lambda _e: save_and_close())
