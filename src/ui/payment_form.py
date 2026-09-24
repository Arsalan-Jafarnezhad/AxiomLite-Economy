"""
Validation helpers shared by the Add Payment form and the Payments-tab
edit dialog. Kept free of any Tkinter imports so they're plain,
easily-testable functions - each raises ValueError with a
user-presentable message on bad input.
"""

from datetime import date as _date

from ..core import ASSET_TYPES

NEW_USER_SENTINEL = "+ Add new user..."
NO_ASSET = "None (regular payment)"
ASSET_CHOICES = [NO_ASSET, *ASSET_TYPES]


def parse_amount(text: str) -> float:
    try:
        amount = float(text.strip().replace(",", ""))
    except ValueError as exc:
        raise ValueError("Please enter a positive number for amount.") from exc
    if amount <= 0:
        raise ValueError("Please enter a positive number for amount.")
    return amount


def parse_date(text: str) -> str:
    text = text.strip()
    try:
        _date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("Please use the format YYYY-MM-DD.") from exc
    return text


def parse_asset(selected_asset: str, quantity_text: str) -> tuple[str | None, float | None]:
    """Returns (asset_type, quantity), both None when `selected_asset` is NO_ASSET."""
    if selected_asset == NO_ASSET:
        return None, None
    try:
        quantity = float(quantity_text.strip().replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"Please enter how much {selected_asset} was involved.") from exc
    if quantity <= 0:
        raise ValueError(f"Please enter how much {selected_asset} was involved.")
    return selected_asset, quantity


def resolve_user_id(selected_user: str, user_lookup: dict) -> int | None:
    if selected_user in (None, "", NEW_USER_SENTINEL):
        return None
    return user_lookup.get(selected_user)
