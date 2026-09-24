"""
Dark theme palette and matplotlib chart helpers, shared across every tab.
"""

import matplotlib.pyplot as plt

THEME = {
    "bg": "#1e1e2e",
    "surface": "#282a3a",
    "fg": "#e0e0e0",
    "muted": "#9a9ab0",
    "accent": "#7aa2f7",
    "accent2": "#bb9af7",
    "positive": "#7dd3a0",
    "negative": "#f28b82",
    "grid": "#3a3d55",
}

# Convenience aliases so tab modules can do `from .theme import BG, FG, ...`
BG = THEME["bg"]
SURFACE = THEME["surface"]
FG = THEME["fg"]
MUTED = THEME["muted"]
ACCENT = THEME["accent"]
ACCENT2 = THEME["accent2"]
POSITIVE = THEME["positive"]
NEGATIVE = THEME["negative"]


def apply_dark_style() -> None:
    """Apply a shared dark matplotlib style. Safe to call multiple times."""
    plt.rcParams.update(
        {
            "figure.facecolor": THEME["bg"],
            "axes.facecolor": THEME["surface"],
            "axes.edgecolor": THEME["grid"],
            "axes.labelcolor": THEME["fg"],
            "text.color": THEME["fg"],
            "xtick.color": THEME["muted"],
            "ytick.color": THEME["muted"],
            "grid.color": THEME["grid"],
            "font.family": "sans-serif",
            "font.size": 10,
        }
    )


def format_money(amount: float, suffix: str = "T") -> str:
    """
    Format a raw number as a signed, thousands-separated money string.
    e.g. format_money(-20000) -> "-20,000 T"
    """
    sign = "-" if amount < 0 else ""
    return f"{sign}{abs(amount):,.0f} {suffix}"


def config_plot():
    """Create a matplotlib Figure/Axes pair pre-styled for the dark theme."""
    apply_dark_style()
    fig, ax = plt.subplots()
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)
    return fig, ax


def draw_m_irt_bar_chart(points):
    """
    Standalone (non-Tk) dark-themed column chart with no gap between bars.
    Args:
        points: A list of (x, y) tuples, e.g. [(1, 10), (2, 15), (3, 7)]
    """
    if len(points) < 1:
        print("At least one point is needed.")
        return

    apply_dark_style()

    x_coords = [p[0] for p in points]
    y_coords = [p[1] * 10e-7 for p in points]
    colors = [POSITIVE if y >= 0 else NEGATIVE for y in y_coords]

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.bar(x_coords, y_coords, width=0.9, color=colors, edgecolor=BG)
    ax.set_xticks(x_coords)
    ax.set_title("Monthly Money Difference", color=FG, fontsize=14, weight="bold")
    ax.set_ylabel("Money (1,000,000 T)")
    ax.set_xlabel("Month")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    plt.show()


def draw_yearly_table(rows):
    """
    Standalone (non-Tk) dark-themed table figure, useful for exporting
    a static image of the monthly breakdown.
    """
    apply_dark_style()

    columns = ("Month", "Status (IRT)", "Status (USDT)")

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.axis("off")

    table = ax.table(cellText=rows, colLabels=columns, loc="center", cellLoc="center")
    for key, cell in table.get_celld().items():
        cell.set_edgecolor(THEME["grid"])
        if key[0] == 0:
            cell.set_facecolor(ACCENT)
            cell.set_text_props(weight="bold", color="#101018")
        else:
            cell.set_facecolor(SURFACE)
            cell.set_text_props(color=FG)

    return "Monthly Breakdown", fig
