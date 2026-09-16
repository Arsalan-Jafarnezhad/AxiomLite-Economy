"""
Personal Money Management App
A dark-themed Tkinter UI for tracking income/expenses, backed by SQLite.
"""

import sys
from datetime import date
from pathlib import Path
from webbrowser import open_new_tab
from tkinter import (
    Tk, Toplevel, Frame, Label, Button, StringVar, BOTH, TOP, BOTTOM, LEFT, RIGHT,
    X, Y, YES, END,
)
from tkinter import ttk, messagebox, filedialog, PhotoImage

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import pyplot as plot
from matplotlib import use

from economy_analyzer import Economy
from utils import THEME, apply_dark_style

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def resource_path(relative_path):
    try:
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).parent
    return base_path / relative_path


BG = THEME["bg"]
SURFACE = THEME["surface"]
FG = THEME["fg"]
MUTED = THEME["muted"]
ACCENT = THEME["accent"]
ACCENT2 = THEME["accent2"]
POSITIVE = THEME["positive"]
NEGATIVE = THEME["negative"]

NEW_USER_SENTINEL = "+ Add new user..."

# File-dialog filters shared by import/export
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


def config_plot():
    apply_dark_style()
    fig, ax = plot.subplots()
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)
    return fig, ax


class App(Economy):
    ICON_SIZE = 20

    def __init__(self, master, year=None, *args, **kwargs):
        super().__init__(year, *args, **kwargs)

        self.master = master
        self.master.configure(bg=BG)
        self.master.resizable(False, False)
        self.master.geometry("1080x720+120+70")
        self.master.iconbitmap(resource_path("assets/images/icon.ico"))
        self.master.title("Personal Money Management App")

        self._init_social_links()
        self._configure_styles()
        self._build_layout()

        self._build_dashboard_tab()
        self._build_add_payment_tab()
        self._build_payments_tab()
        self._build_users_tab()
        self._build_import_export_tab()

        self.refresh_all()

    # ------------------------------------------------------------------
    # Social icons (top-right header)
    # ------------------------------------------------------------------
    def _init_social_links(self):
        self.github_url = "https://github.com/arsalan-jafarnezhad/"
        self.telegram_url = "https://t.me/axiomlite/"
        self.linkedin_url = "https://linkedin.com/in/arsalan-jafarnezhad/"

        self.icon_fallback_font = ("Segoe UI", 9, "bold")
        self.github_icon = self.load_icon(resource_path("assets/images/github.png"), self.ICON_SIZE)
        self.telegram_icon = self.load_icon(resource_path("assets/images/telegram.png"), self.ICON_SIZE)
        self.linkedin_icon = self.load_icon(resource_path("assets/images/linkedin.png"), self.ICON_SIZE)

    def load_icon(self, path, size):
        """Load and resize an icon safely. Returns None if unavailable so
        callers can fall back to a text button instead of crashing."""
        try:
            if PIL_AVAILABLE:
                img = Image.open(path).convert("RGBA")
                img = img.resize((size, size), Image.LANCZOS)
                return ImageTk.PhotoImage(img)

            img = PhotoImage(file=path)
            current_w = img.width() or size
            if current_w > size:
                factor = max(1, round(current_w / size))
                img = img.subsample(factor, factor)
            elif current_w < size:
                factor = max(1, round(size / current_w))
                img = img.zoom(factor, factor)
            return img
        except Exception:
            return None

    def open_link(self, url):
        try:
            open_new_tab(url)
        except Exception:
            messagebox.showerror("Could Not Open Link", f"Unable to open:\n{url}")

    def build_social_icons(self, parent):
        Label(parent, text="Follow", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(
            side=LEFT, padx=(0, 8)
        )
        icons = Frame(parent, bg=BG)
        icons.pack(side=LEFT)

        self.make_social_button(icons, self.github_icon, "GH", self.github_url)
        self.make_social_button(icons, self.telegram_icon, "TG", self.telegram_url)
        self.make_social_button(icons, self.linkedin_icon, "in", self.linkedin_url)

    def make_social_button(self, parent, icon, fallback_text, url):
        common_kwargs = dict(
            command=lambda: self.open_link(url),
            bg=BG,
            activebackground=SURFACE,
            bd=0,
            relief="flat",
            cursor="hand2",
            highlightthickness=0,
        )
        if icon is not None:
            btn = Button(parent, image=icon, **common_kwargs)
            btn.image = icon  # keep a reference so it isn't garbage collected
        else:
            btn = Button(
                parent, text=fallback_text, fg=FG, font=self.icon_fallback_font,
                width=3, **common_kwargs,
            )
        btn.pack(side=LEFT, padx=3)
        btn.bind("<Enter>", lambda e: btn.config(bg=SURFACE))
        btn.bind("<Leave>", lambda e: btn.config(bg=BG))
        return btn

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Dark.TFrame", background=BG)
        style.configure("Sidebar.TFrame", background=SURFACE)

        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=SURFACE,
            foreground=MUTED,
            padding=(16, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", BG)],
            foreground=[("selected", ACCENT)],
        )

        style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Field.TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))

        style.configure(
            "Accent.TButton", background=ACCENT, foreground="#101018",
            font=("Segoe UI", 10, "bold"), padding=8, borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", ACCENT2)])

        style.configure(
            "Ghost.TButton", background=SURFACE, foreground=FG,
            font=("Segoe UI", 10), padding=8, borderwidth=1,
        )
        style.map("Ghost.TButton", background=[("active", "#33364a")])

        style.configure(
            "Danger.TButton", background=NEGATIVE, foreground="#101018",
            font=("Segoe UI", 10, "bold"), padding=6, borderwidth=0,
        )

        style.configure("TEntry", fieldbackground=SURFACE, foreground=FG, insertcolor=FG, padding=6)
        style.configure("TCombobox", fieldbackground=SURFACE, foreground=FG, background=SURFACE)
        style.configure("TRadiobutton", background=BG, foreground=FG, font=("Segoe UI", 10))

        style.configure(
            "Treeview", background=SURFACE, foreground=FG, fieldbackground=SURFACE,
            rowheight=28, borderwidth=0,
        )
        style.configure(
            "Treeview.Heading", background="#33364a", foreground=FG,
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#101018")])

    # ------------------------------------------------------------------
    # Generic Treeview column sorting (click a header to sort by it)
    # ------------------------------------------------------------------
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

    def _build_layout(self):
        self.root_frame = Frame(self.master, bg=BG)
        self.root_frame.pack(expand=YES, fill=BOTH)

        header = Frame(self.root_frame, bg=BG)
        header.pack(side=TOP, fill=X, padx=20, pady=(16, 0))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        header_left = Frame(header, bg=BG)
        header_left.grid(row=0, column=0, sticky="w")
        Label(
            header_left, text="💰 Personal Money Management App", bg=BG, fg=FG,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w")
        self.usd_label = Label(header_left, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        self.usd_label.pack(anchor="w", pady=(2, 0))

        header_right = Frame(header, bg=BG)
        header_right.grid(row=0, column=1, sticky="ne")
        self.build_social_icons(header_right)

        self.notebook = ttk.Notebook(self.root_frame)
        self.notebook.pack(expand=YES, fill=BOTH, padx=16, pady=16)

        self.dashboard_tab = Frame(self.notebook, bg=BG)
        self.add_payment_tab = Frame(self.notebook, bg=BG)
        self.payments_tab = Frame(self.notebook, bg=BG)
        self.users_tab = Frame(self.notebook, bg=BG)
        self.import_export_tab = Frame(self.notebook, bg=BG)

        self.notebook.add(self.dashboard_tab, text="  Dashboard  ")
        self.notebook.add(self.add_payment_tab, text="  Add Payment  ")
        self.notebook.add(self.payments_tab, text="  Payments  ")
        self.notebook.add(self.users_tab, text="  Users  ")
        self.notebook.add(self.import_export_tab, text="  Import / Export  ")

    # ------------------------------------------------------------------
    # Dashboard tab
    # ------------------------------------------------------------------
    def _build_dashboard_tab(self):
        top_bar = Frame(self.dashboard_tab, bg=BG)
        top_bar.pack(side=TOP, fill=X, pady=(0, 8))

        self.summary_label = Label(top_bar, text="", bg=BG, fg=FG, font=("Segoe UI", 11), justify=LEFT)
        self.summary_label.pack(side=LEFT)

        ttk.Button(
            top_bar, text="⟳ Switch Graph", style="Ghost.TButton", command=self.switch_graphs
        ).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(
            top_bar, text="↻ Refresh", style="Accent.TButton", command=self.refresh_all
        ).pack(side=RIGHT)

        self.fig, self.ax = config_plot()
        self.plot_frame = Frame(self.dashboard_tab, bg=BG)
        self.plot_frame.pack(side=TOP, expand=YES, fill=BOTH)

        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.get_tk_widget().configure(bg=BG)
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        toolbar_frame = Frame(self.dashboard_tab, bg=BG)
        toolbar_frame.pack(side=BOTTOM, fill=X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.config(background=BG)
        try:
            toolbar._message_label.config(background=BG, foreground=MUTED)
        except Exception:
            pass
        for child in toolbar.winfo_children():
            try:
                child.config(background=BG)
            except Exception:
                pass
        toolbar.update()

        self.graphIndex = 0
        self.graphs = {0: self.draw_bar_chart, 1: self.draw_table}

    def on_key_press(self, event):
        if event.key and event.key.upper() == "W":
            self.switch_graphs()

    def switch_graphs(self):
        self.graphIndex = (self.graphIndex + 1) % len(self.graphs)
        self._safe_render(self.graphs[self.graphIndex])
        self.canvas.draw()

    def _safe_render(self, func):
        try:
            func()
        except Exception as exc:  # noqa: BLE001
            self.ax.clear()
            self.ax.axis("off")
            self.ax.text(0.5, 0.5, f"No data available\n({exc})", ha="center", va="center", color=MUTED)

    def draw_bar_chart(self):
        points = self.monthly_money_differences
        self.ax.clear()

        if not points:
            self.ax.axis("off")
            self.ax.text(0.5, 0.5, "No transactions yet", ha="center", va="center", color=MUTED)
            return

        x_coords = [p[0] for p in points]
        y_coords = [p[1] * 10e-7 for p in points]
        colors = [POSITIVE if y >= 0 else NEGATIVE for y in y_coords]

        self.ax.bar(x_coords, y_coords, width=0.9, color=colors, edgecolor=BG, label="Monthly change")
        self.ax.set(title="Monthly Money Difference")
        self.ax.set_xticks(x_coords)
        self.ax.set_xlabel("Month")
        self.ax.set_ylabel("Money (1,000,000 T)")
        self.ax.axhline(0, color=MUTED, linewidth=0.8)
        self.ax.grid(axis="y", linestyle="--", alpha=0.35)
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.legend(facecolor=SURFACE, edgecolor=BG, labelcolor=FG)

    def draw_table(self):
        self.ax.clear()
        self.ax.axis("off")
        rows = self.monthly_table_data

        if not rows:
            self.ax.text(0.5, 0.5, "No monthly data yet", ha="center", va="center", color=MUTED)
            return

        columns = ("Month", "Status (IRT)", "Status (USDT)")
        table = self.ax.table(cellText=rows, colLabels=columns, loc="center", cellLoc="center")
        for key, cell in table.get_celld().items():
            cell.set_edgecolor(THEME["grid"])
            if key[0] == 0:
                cell.set_facecolor(ACCENT)
                cell.set_text_props(weight="bold", color="#101018")
            else:
                cell.set_facecolor(SURFACE)
                cell.set_text_props(color=FG)
        self.ax.set(title="Monthly Money Differences")

    # ------------------------------------------------------------------
    # Add Payment tab
    # ------------------------------------------------------------------
    def _build_add_payment_tab(self):
        form = Frame(self.add_payment_tab, bg=BG)
        form.pack(side=TOP, fill=X, padx=40, pady=30)

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

        ttk.Button(
            form, text="💾  Save Payment", style="Accent.TButton", command=self._on_save_payment
        ).grid(row=6, column=1, sticky="w", pady=(20, 0))

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
        amount_text = self.amount_var.get().strip()
        try:
            amount = float(amount_text.replace(",", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid amount", "Please enter a positive number for amount.")
            return

        date_text = self.date_var.get().strip()
        try:
            date.fromisoformat(date_text)
        except ValueError:
            messagebox.showerror("Invalid date", "Please use the format YYYY-MM-DD.")
            return

        selected_user = self.user_var.get()
        user_id = None if selected_user in (None, "", NEW_USER_SENTINEL) else self._user_lookup.get(selected_user)

        is_income = self.type_var.get() == "income"
        reason = self.reason_var.get().strip()

        try:
            self.add_transaction(amount, is_income, date_text, user_id, reason)
        except ValueError as exc:
            messagebox.showerror("Couldn't save payment", str(exc))
            return

        messagebox.showinfo("Saved", "Payment saved successfully.")
        self.amount_var.set("")
        self.reason_var.set("")
        self.refresh_all()

    # ------------------------------------------------------------------
    # Payments tab (full table view of every stored transaction)
    # ------------------------------------------------------------------
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

        columns = ("id", "date", "type", "amount", "person", "reason")
        self.payments_tree = ttk.Treeview(container, columns=columns, show="headings", height=18)
        headings = {
            "id": ("ID", 40), "date": ("Date", 100), "type": ("Type", 60),
            "amount": ("Amount (T)", 130), "person": ("Person", 160), "reason": ("Reason", 260),
        }
        for key, (label, width) in headings.items():
            self.payments_tree.heading(key, text=label)
            anchor = "center" if key in ("id", "type") else "w"
            self.payments_tree.column(key, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.payments_tree.yview)
        self.payments_tree.configure(yscrollcommand=scrollbar.set)
        self.payments_tree.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.payments_tree.tag_configure("income", foreground=POSITIVE)
        self.payments_tree.tag_configure("expense", foreground=NEGATIVE)
        self._make_sortable(self.payments_tree, numeric_columns={"id", "amount"})

    def _refresh_payments_tree(self):
        self.payments_tree.delete(*self.payments_tree.get_children())
        for row in self.get_all_transactions():
            sign = "+" if row["is_income"] else "-"
            tag = "income" if row["is_income"] else "expense"
            self.payments_tree.insert(
                "", END,
                values=(
                    row["id"], row["date"], sign, f"{row['amount']:,.0f}",
                    row["user_name"] or "-", row["reason"] or "-",
                ),
                tags=(tag,),
            )

    def _on_delete_payment_click(self):
        selection = self.payments_tree.selection()
        if not selection:
            messagebox.showwarning("Nothing selected", "Select a payment to delete.")
            return
        transaction_id = self.payments_tree.item(selection[0])["values"][0]
        if messagebox.askyesno("Delete payment", f"Delete payment #{transaction_id}? This can't be undone."):
            self.delete_transaction(transaction_id)
            self.refresh_all()

    # ------------------------------------------------------------------
    # Users tab
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Import / Export tab
    # ------------------------------------------------------------------
    def _build_import_export_tab(self):
        container = Frame(self.import_export_tab, bg=BG)
        container.pack(side=TOP, fill=BOTH, expand=YES, padx=40, pady=30)

        ttk.Label(container, text="Import Payments", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text=(
                "Import a ledger .txt, .csv, .json, .toml, .yaml, .sql, or .sqlite3/.db file. "
                "New people are added automatically."
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
        export_labels = {
            "json": "Export JSON", "csv": "Export CSV", "txt": "Export TXT",
            "toml": "Export TOML", "yaml": "Export YAML", "sql": "Export SQL",
        }
        for fmt, label in export_labels.items():
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

    # ------------------------------------------------------------------
    # Shared refresh
    # ------------------------------------------------------------------
    def refresh_all(self):
        self.monthly_money_differences = self._get_monthly_money_differences()
        self.monthly_table_data = self._get_monthly_table_data()

        money_difference = self.get_money_difference()
        sign = "+" if money_difference >= 0 else ""
        self.summary_label.config(
            text=(
                f"Total Money: {self.get_total_money():,.0f} T   "
                f"({self.get_total_money_usdt():,.2f} $)     "
                f"This Year: {sign}{money_difference:,.0f} T"
            )
        )
        self.usd_label.config(text=f"1 USDT ≈ {self.usdt_irt:,.0f} T")

        self._refresh_user_combo(keep_selection=self.user_var.get() if hasattr(self, "user_var") else None)
        self._refresh_users_tree()
        self._refresh_payments_tree()
        self._safe_render(self.graphs[self.graphIndex])
        if hasattr(self, "canvas"):
            self.canvas.draw()


def main():
    use("TkAgg")
    root = Tk()
    # root.geometry("1100x720+120+70")
    # root.minsize(900, 620)
    # root.title("Personal Money Management App")
    # root.configure(bg=BG)

    try:
        root.iconbitmap(resource_path("assets/images/icon.ico"))
    except Exception:
        pass  # icon is optional; don't crash the app if it's missing

    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()