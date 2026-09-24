"""
Generic click-to-sort behavior for ttk.Treeview headers, shared by every
table in the app (Payments, Users, ...).
"""

from tkinter import ttk


class SortableTreeviewMixin:
    """Mixin providing _make_sortable() for any ttk.Treeview."""

    def _make_sortable(self, tree: ttk.Treeview, numeric_columns: set[str] | None = None):
        """
        Bind click-to-sort behavior to every column heading in `tree`.
        `numeric_columns` lists columns that should sort as numbers
        (with commas stripped) instead of plain text. Clicking the same
        header again reverses the sort direction.
        """
        numeric_columns = numeric_columns or set()
        if not hasattr(self, "_sort_state"):
            self._sort_state = {}
        self._sort_state[tree] = {"column": None, "reverse": False}

        for column in tree["columns"]:
            tree.heading(
                column,
                text=tree.heading(column, "text"),
                command=lambda c=column: self._sort_treeview(tree, c, numeric_columns),
            )

    def _sort_treeview(self, tree: ttk.Treeview, column: str, numeric_columns: set[str]):
        state = self._sort_state[tree]
        reverse = not state["reverse"] if state["column"] == column else False

        def sort_key(item_id):
            value = tree.set(item_id, column)
            if column in numeric_columns:
                try:
                    return float(str(value).replace(",", ""))
                except ValueError:
                    return float("-inf")
            return str(value).lower()

        items = sorted(tree.get_children(""), key=sort_key, reverse=reverse)
        for index, item_id in enumerate(items):
            tree.move(item_id, "", index)

        state["column"] = column
        state["reverse"] = reverse

        # Small arrow indicator on the active column, like a spreadsheet.
        for other_column in tree["columns"]:
            base_text = tree.heading(other_column, "text").rstrip(" ▲▼")
            if other_column == column:
                arrow = " ▼" if reverse else " ▲"
                tree.heading(other_column, text=base_text + arrow)
            else:
                tree.heading(other_column, text=base_text)
