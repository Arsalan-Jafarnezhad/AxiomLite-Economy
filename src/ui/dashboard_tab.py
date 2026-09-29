"""
Dashboard tab: monthly bar chart / table toggle, embedded via
matplotlib's Tk backend. The bar chart has an optional "Show USDT" /
"Show GOLD" filter: when checked, that month's investment activity
(valued at today's live price) is drawn as an extra bar series next to
the cash-flow bars, so you can see money that moved into assets without
it being counted as spending.
"""

from tkinter import BooleanVar, Frame, Label, ttk, BOTH, BOTTOM, LEFT, RIGHT, TOP, X, YES

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from .theme import ACCENT, ACCENT2, BG, FG, MUTED, NEGATIVE, POSITIVE, SURFACE, THEME, config_plot


class DashboardTabMixin:
    """Mixin providing the Dashboard tab (bar chart / monthly table)."""

    def _build_dashboard_tab(self):
        container = Frame(self.dashboard_tab, bg=BG)
        container.pack(side=TOP, fill=BOTH, expand=YES, padx=24, pady=20)

        top_bar = Frame(container, bg=BG)
        top_bar.pack(side=TOP, fill=X, pady=(0, 8))

        ttk.Label(top_bar, text="Cash Flow Chart", style="Title.TLabel").pack(side=LEFT)

        ttk.Button(
            top_bar, text="⟳ Switch Graph", style="Ghost.TButton", command=self.switch_graphs
        ).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(
            top_bar, text="↻ Refresh", style="Accent.TButton", command=self.refresh_all
        ).pack(side=RIGHT, padx=(8, 0))

        filter_bar = Frame(container, bg=BG)
        filter_bar.pack(side=TOP, fill=X, pady=(0, 8))
        Label(filter_bar, text="Show on chart:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)

        self.show_usdt_var = BooleanVar(value=False)
        self.show_gold_var = BooleanVar(value=False)
        ttk.Checkbutton(
            filter_bar, text="USDT", variable=self.show_usdt_var, command=self._on_chart_filter_changed
        ).pack(side=LEFT, padx=(10, 0))
        ttk.Checkbutton(
            filter_bar, text="GOLD", variable=self.show_gold_var, command=self._on_chart_filter_changed
        ).pack(side=LEFT, padx=(10, 0))

        self.fig, self.ax = config_plot()
        self.plot_frame = Frame(container, bg=BG)
        self.plot_frame.pack(side=TOP, expand=YES, fill=BOTH)

        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.get_tk_widget().configure(bg=BG)
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        toolbar_frame = Frame(container, bg=BG)
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

    def _on_chart_filter_changed(self):
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
        self.ax.clear()

        # Each series: (label, {month: value_in_T}, positive_color, negative_color)
        series = []
        cash_points = self.monthly_money_differences
        if cash_points:
            series.append(("Cash flow", dict(cash_points), POSITIVE, NEGATIVE))
        if self.show_usdt_var.get():
            usdt_points = self._get_monthly_asset_totals("USDT")
            if usdt_points:
                series.append(("USDT", dict(usdt_points), ACCENT, ACCENT))
        if self.show_gold_var.get():
            gold_points = self._get_monthly_asset_totals("GOLD")
            if gold_points:
                series.append(("GOLD", dict(gold_points), ACCENT2, ACCENT2))

        if not series:
            self.ax.axis("off")
            self.ax.text(0.5, 0.5, "No transactions yet", ha="center", va="center", color=MUTED)
            return

        months = sorted({month for _, data, *_ in series for month in data})
        series_count = len(series)
        group_width = 0.85
        bar_width = group_width / series_count

        for index, (label, data, pos_color, neg_color) in enumerate(series):
            offset = -group_width / 2 + bar_width * index + bar_width / 2
            x_coords = [month + offset for month in months]
            y_coords = [data.get(month, 0) * 10e-7 for month in months]
            colors = [pos_color if y >= 0 else neg_color for y in y_coords]
            self.ax.bar(x_coords, y_coords, width=bar_width * 0.9, color=colors, edgecolor=BG, label=label)

        self.ax.set(title="Monthly Overview")
        self.ax.set_xticks(months)
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
