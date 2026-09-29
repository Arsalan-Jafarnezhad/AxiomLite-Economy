"""
Info tab: net worth and every derived calculation (USDT/GOLD/USD
holdings, live prices, cash flow) laid out as readable stat cards and
tables, kept separate from the Dashboard's chart.
"""

from tkinter import Frame, Label, ttk, BOTH, LEFT, TOP, X, YES

from .theme import ACCENT, ACCENT2, BG, FG, MUTED, SURFACE


class InfoTabMixin:
    """Mixin providing the Info tab (net worth + all derived stats)."""

    def _build_info_tab(self):
        container = Frame(self.info_tab, bg=BG)
        container.pack(side=TOP, fill=BOTH, expand=YES, padx=40, pady=30)

        ttk.Label(container, text="Overview", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Your net worth and how it's made up, calculated from every stored payment.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 20))

        # ---- Top row: headline numbers as cards ----
        cards_row = Frame(container, bg=BG)
        cards_row.pack(side=TOP, fill=X, pady=(0, 24))
        for i in range(4):
            cards_row.columnconfigure(i, weight=1)

        self._info_cards = {}
        card_titles = {
            "total_irt": "Total Net Worth (T)",
            "total_usdt": "Total Net Worth ($)",
            "cash_year": "Cash Flow This Year",
            "avg_month": "Avg. Monthly Cash Flow",
        }
        for index, (key, title) in enumerate(card_titles.items()):
            card, value_label = self._make_stat_card(cards_row, title)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 8, 0))
            self._info_cards[key] = value_label

        # ---- Holdings & live prices ----
        ttk.Label(container, text="Holdings & Live Prices", style="Title.TLabel").pack(
            anchor="w", pady=(10, 6)
        )
        self._info_holdings = self._build_info_table(
            container,
            [
                ("usd_cash", "USD cash held"),
                ("base_usdt", "Starting USDT (before tracking)"),
                ("bought_usdt", "USDT bought via tracked payments"),
                ("total_usdt", "Total USDT held"),
                ("total_usdt_with_usd", "Total USDT (USD counted 1:1)"),
                ("gold_holdings", "Gold held (grams)"),
                ("usdt_price", "1 USDT price"),
                ("gold_price", "1g Gold price"),
            ],
        )

        # ---- Net worth breakdown ----
        ttk.Label(container, text="Net Worth Breakdown", style="Title.TLabel").pack(
            anchor="w", pady=(20, 6)
        )
        self._info_breakdown = self._build_info_table(
            container,
            [
                ("base", "Starting Balance"),
                ("usd_line", "+ USD & Starting USDT Value"),
                ("usdt_line", "+ Tracked USDT Holdings Value"),
                ("gold_line", "+ Gold Holdings Value"),
                ("cash_line", "+ Cash Flow This Year"),
                ("total_line", "= Total Net Worth"),
            ],
            highlight_last=True,
        )

    def _make_stat_card(self, parent, title):
        card = Frame(parent, bg=SURFACE)
        Label(card, text=title, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(
            anchor="w", padx=14, pady=(12, 0)
        )
        value_label = Label(card, text="-", bg=SURFACE, fg=ACCENT, font=("Segoe UI", 16, "bold"))
        value_label.pack(anchor="w", padx=14, pady=(0, 12))
        return card, value_label

    def _build_info_table(self, parent, rows, highlight_last=False):
        table = Frame(parent, bg=SURFACE)
        table.pack(side=TOP, fill=X, pady=(0, 4))
        table.columnconfigure(1, weight=1)

        labels = {}
        last_index = len(rows) - 1
        for index, (key, title) in enumerate(rows):
            is_last = highlight_last and index == last_index
            label_color = ACCENT if is_last else FG
            value_color = ACCENT if is_last else ACCENT2
            font = ("Segoe UI", 10, "bold") if is_last else ("Segoe UI", 10)

            Label(table, text=title, bg=SURFACE, fg=label_color, font=font, anchor="w").grid(
                row=index, column=0, sticky="w", padx=14, pady=6
            )
            value_label = Label(table, text="-", bg=SURFACE, fg=value_color, font=("Segoe UI", 10, "bold"), anchor="e")
            value_label.grid(row=index, column=1, sticky="e", padx=14, pady=6)
            labels[key] = value_label
        return labels

    def _refresh_info_tab(self):
        base_usdt = self.get_asset_holdings("USDT")
        gold_holdings = self.get_asset_holdings("GOLD")
        usdt_value = self.get_crypto_money()
        gold_value = self.get_gold_money()
        dollars_value = self.get_dollars_money()
        cash_year = self.get_money_difference()
        total_irt = self.get_total_money()
        sign = "+" if cash_year >= 0 else ""

        total_usdt_held = self._base_usdt_amount + base_usdt
        total_usdt_with_usd = self._base_usd_amount + total_usdt_held

        self._info_cards["total_irt"].config(text=f"{total_irt:,.0f} T")
        self._info_cards["total_usdt"].config(text=f"{self.get_total_money_usdt():,.2f} $")
        self._info_cards["cash_year"].config(text=f"{sign}{cash_year:,.0f} T")
        self._info_cards["avg_month"].config(text=f"{self.get_average_monthly_income():,.0f} T")

        holdings = self._info_holdings
        holdings["usd_cash"].config(text=f"{self._base_usd_amount:,.4g} USD")
        holdings["base_usdt"].config(text=f"{self._base_usdt_amount:,.4g} USDT")
        holdings["bought_usdt"].config(text=f"{base_usdt:,.4g} USDT")
        holdings["total_usdt"].config(text=f"{total_usdt_held:,.4g} USDT")
        holdings["total_usdt_with_usd"].config(text=f"{total_usdt_with_usd:,.4g} USDT")
        holdings["gold_holdings"].config(text=f"{gold_holdings:,.4g} g")
        holdings["usdt_price"].config(text=f"{self.usdt_irt:,.0f} T")
        holdings["gold_price"].config(text=f"{self.gold_irt:,.0f} T")

        breakdown = self._info_breakdown
        breakdown["base"].config(text=f"{self._base_money:,.0f} T")
        breakdown["usd_line"].config(text=f"{dollars_value:,.0f} T")
        breakdown["usdt_line"].config(text=f"{usdt_value:,.0f} T")
        breakdown["gold_line"].config(text=f"{gold_value:,.0f} T")
        breakdown["cash_line"].config(text=f"{sign}{cash_year:,.0f} T")
        breakdown["total_line"].config(text=f"{total_irt:,.0f} T")
