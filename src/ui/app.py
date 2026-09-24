"""
Personal Money Management App - dark-themed Tkinter UI.

The App class itself only owns window-shell concerns (styling, layout,
tab registration, the shared refresh_all()); each tab's content and
behavior lives in its own mixin module next to this file.
"""

from tkinter import Tk, Frame, Label, ttk, BOTH, TOP, X, YES
from tkinter import PhotoImage

from ..config import ICON_PATH
from ..economy import Economy
from .add_payment_tab import AddPaymentTabMixin
from .dashboard_tab import DashboardTabMixin
from .import_export_tab import ImportExportTabMixin
from .payments_tab import PaymentsTabMixin
from .social import SocialLinksMixin
from .sorting import SortableTreeviewMixin
from .theme import ACCENT, ACCENT2, BG, FG, MUTED, NEGATIVE, SURFACE
from .users_tab import UsersTabMixin


class App(
    Economy,
    SocialLinksMixin,
    SortableTreeviewMixin,
    DashboardTabMixin,
    AddPaymentTabMixin,
    PaymentsTabMixin,
    UsersTabMixin,
    ImportExportTabMixin,
):
    def __init__(self, master, year=None, *args, **kwargs):
        super().__init__(year, *args, **kwargs)

        self.master = master
        self.master.configure(bg=BG)

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
    # Window shell
    # ------------------------------------------------------------------
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
        self.holdings_label = Label(header_left, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        self.holdings_label.pack(anchor="w", pady=(2, 0))

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

        usdt_holdings = self.get_asset_holdings("USDT")
        gold_holdings = self.get_asset_holdings("GOLD")
        self.holdings_label.config(
            text=(
                f"Holdings: {usdt_holdings:,.4g} USDT (~{self.get_crypto_money():,.0f} T)  ·  "
                f"{gold_holdings:,.4g} g Gold (~{self.get_gold_money():,.0f} T)"
            )
        )

        self._refresh_user_combo(keep_selection=self.user_var.get() if hasattr(self, "user_var") else None)
        self._refresh_users_tree()
        self._refresh_payments_tree()
        self._safe_render(self.graphs[self.graphIndex])
        if hasattr(self, "canvas"):
            self.canvas.draw()


def main():
    from matplotlib import use

    use("TkAgg")
    root = Tk()
    root.geometry("1100x720+120+70")
    root.minsize(900, 620)
    root.title("Personal Money Management App")
    root.configure(bg=BG)

    try:
        root.iconbitmap(ICON_PATH)
    except Exception:
        pass  # icon is optional; don't crash the app if it's missing

    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
