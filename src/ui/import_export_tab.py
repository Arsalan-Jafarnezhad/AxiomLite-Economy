"""
Import/Export tab: import from any supported file format, export to
json/csv/txt/toml/yaml/sql.
"""

from tkinter import Frame, Label, ttk, BOTH, LEFT, TOP, YES
from tkinter import filedialog, messagebox

from .theme import BG, MUTED

IMPORT_FILETYPES = [
    ("All supported", "*.txt *.csv *.json *.toml *.yaml *.yml *.sql *.sqlite3 *.db"),
    ("Ledger text", "*.txt"),
    ("CSV", "*.csv"),
    ("JSON", "*.json"),
    ("TOML", "*.toml"),
    ("YAML", "*.yaml *.yml"),
    ("SQL script", "*.sql"),
    ("SQLite database", "*.sqlite3 *.db"),
]

EXPORT_FORMATS = {
    "json": [("JSON files", "*.json")],
    "csv": [("CSV files", "*.csv")],
    "txt": [("Text ledger", "*.txt")],
    "toml": [("TOML files", "*.toml")],
    "yaml": [("YAML files", "*.yaml *.yml")],
    "sql": [("SQL dump", "*.sql")],
}

EXPORT_LABELS = {
    "json": "Export JSON", "csv": "Export CSV", "txt": "Export TXT",
    "toml": "Export TOML", "yaml": "Export YAML", "sql": "Export SQL",
}


class ImportExportTabMixin:
    """Mixin providing the Import/Export tab."""

    def _build_import_export_tab(self):
        container = Frame(self.import_export_tab, bg=BG)
        container.pack(side=TOP, fill=BOTH, expand=YES, padx=40, pady=30)

        ttk.Label(container, text="Import Payments", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text=(
                "Import a ledger .txt, .csv, .json, .toml, .yaml, .sql, or .sqlite3/.db file. "
                "New people are added automatically. A reason like \"GOLD 14000000\" or "
                "\"USDT 70000\" (price per unit) marks that line as buying an asset "
                "instead of spending."
            ),
            style="Subtitle.TLabel",
            wraplength=700,
            justify=LEFT,
        ).pack(anchor="w", pady=(0, 12))

        ttk.Button(
            container, text="📂  Choose File to Import", style="Accent.TButton",
            command=self._on_import_file_click,
        ).pack(anchor="w")

        self.import_result_label = Label(
            container, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), justify=LEFT, wraplength=700
        )
        self.import_result_label.pack(anchor="w", pady=(10, 30))

        ttk.Label(container, text="Export Payments", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Export all stored transactions for the current year to a file.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        export_row = Frame(container, bg=BG)
        export_row.pack(anchor="w")
        for fmt, label in EXPORT_LABELS.items():
            ttk.Button(
                export_row, text=label, style="Ghost.TButton",
                command=lambda f=fmt: self._on_export_click(f),
            ).pack(side=LEFT, padx=(0, 8))

    def _on_import_file_click(self):
        path = filedialog.askopenfilename(title="Select a file to import", filetypes=IMPORT_FILETYPES)
        if not path:
            return

        summary = self.import_ledger_file(path)

        message = f"Imported {summary['imported']} row(s), skipped {summary['skipped']}."
        if summary["errors"]:
            preview = "\n".join(summary["errors"][:5])
            remaining = len(summary["errors"]) - 5
            more = f"\n... and {remaining} more" if remaining > 0 else ""
            message += f"\n\nIssues:\n{preview}{more}"

        self.import_result_label.config(text=message)
        messagebox.showinfo("Import complete", f"Imported {summary['imported']} row(s).")
        self.refresh_all()

    def _on_export_click(self, fmt: str):
        path = filedialog.asksaveasfilename(
            title=f"Export as {fmt.upper()}", defaultextension=f".{fmt}", filetypes=EXPORT_FORMATS[fmt],
        )
        if not path:
            return

        exporters = {
            "json": self.export_json, "csv": self.export_csv, "txt": self.export_txt,
            "toml": self.export_toml, "yaml": self.export_yaml, "sql": self.export_sql,
        }
        try:
            count = exporters[fmt](path)
        except RuntimeError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        except OSError as exc:
            messagebox.showerror("Export failed", f"Couldn't write the file:\n{exc}")
            return

        messagebox.showinfo("Export complete", f"Exported {count} row(s) to:\n{path}")
