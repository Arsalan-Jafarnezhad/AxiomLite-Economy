"""
Users tab: sortable list of users (payment counterparties) with add/delete.
"""

from tkinter import Frame, StringVar, ttk, BOTH, LEFT, TOP, X, YES, END
from tkinter import messagebox

from .theme import BG


class UsersTabMixin:
    """Mixin providing the Users tab."""

    def _build_users_tab(self):
        container = Frame(self.users_tab, bg=BG)
        container.pack(side=TOP, fill=BOTH, expand=YES, padx=40, pady=30)

        ttk.Label(container, text="Users", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Payments reference a user by ID, so use this list to avoid duplicate/misspelled names.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        add_row = Frame(container, bg=BG)
        add_row.pack(side=TOP, fill=X, pady=(0, 16))
        self.new_user_var = StringVar()
        ttk.Entry(add_row, textvariable=self.new_user_var, width=30).pack(side=LEFT)
        ttk.Button(
            add_row, text="+ Add User", style="Accent.TButton", command=self._on_add_user_click
        ).pack(side=LEFT, padx=(10, 0))
        ttk.Button(
            add_row, text="🗑 Delete Selected", style="Danger.TButton", command=self._on_delete_user_click
        ).pack(side=LEFT, padx=(10, 0))

        self.users_tree = ttk.Treeview(container, columns=("id", "name"), show="headings", height=12)
        self.users_tree.heading("id", text="ID")
        self.users_tree.heading("name", text="Name")
        self.users_tree.column("id", width=60, anchor="center")
        self.users_tree.column("name", width=300, anchor="w")
        self.users_tree.pack(side=TOP, fill=BOTH, expand=YES)
        self._make_sortable(self.users_tree, numeric_columns={"id"})

    def _on_add_user_click(self):
        name = self.new_user_var.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Please type a name first.")
            return
        try:
            self.add_user(name)
        except ValueError as exc:
            messagebox.showerror("Couldn't add user", str(exc))
            return
        self.new_user_var.set("")
        self._refresh_users_tree()
        self._refresh_user_combo()

    def _on_delete_user_click(self):
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Nothing selected", "Select a user to delete.")
            return
        item = self.users_tree.item(selection[0])
        user_id, name = item["values"]
        if messagebox.askyesno(
            "Delete user",
            f"Delete '{name}'? Existing payments will keep their history but lose the person link.",
        ):
            self.delete_user(user_id)
            self._refresh_users_tree()
            self._refresh_user_combo()

    def _refresh_users_tree(self):
        self.users_tree.delete(*self.users_tree.get_children())
        for user_id, name in self.get_users():
            self.users_tree.insert("", END, values=(user_id, name))
