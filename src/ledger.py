"""
Parsing for the ledger ".txt" line format, e.g.:

    + 500,000 [2026/06/21] [Father] [Monthly Income]
    - 18,400 [2026/06/26] [Sepehr Jalil Jamshidi] [Payback Of Ice Cream]

Investment shorthand: a reason of "GOLD <price>" or "USDT <price>" marks
the line as buying/selling that asset at the given price-per-unit, e.g.:

    - 14,000,000 [2026/07/10] [Nobitex] [GOLD 14000000]

means "paid 14,000,000 T total, at a price of 14,000,000 T per unit" ->
1 unit of gold bought. The quantity is derived as amount / price. This
is a convenience for hand-written/legacy ledgers; the app's own UI
records asset_type/asset_quantity directly instead of relying on it.
"""

import re

_LEDGER_LINE_RE = re.compile(
    r"^\s*(?P<sign>[+-])\s*(?P<amount>[\d,]+(?:\.\d+)?)\s*(?P<rest>.*)$"
)
_TAG_RE = re.compile(r"\[(.*?)\]")

ASSET_TYPES = ("USDT", "GOLD")

# "GOLD 14000000" -> bought at a price of 14,000,000 T per unit;
# quantity is derived as amount / price. Handy for hand-written notes.
_ASSET_PRICE_RE = re.compile(
    r"^\s*(?P<asset>" + "|".join(ASSET_TYPES) + r")\s+(?P<price>[\d,]+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)
# "USDT QTY 3.25" -> exact quantity, no derivation needed. Used by this
# app's own .txt export so a round-trip import loses no precision.
_ASSET_QTY_RE = re.compile(
    r"^\s*(?P<asset>" + "|".join(ASSET_TYPES) + r")\s+QTY\s+(?P<quantity>[\d,]+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)


def normalize_date(raw_date: str) -> str:
    """Convert "2026/06/21" (or already-ISO "2026-06-21") into "YYYY-MM-DD"."""
    return raw_date.strip().replace("/", "-")


def parse_asset_shorthand(reason: str, amount: float) -> tuple[str, float] | None:
    """
    Parse an investment-transaction shorthand out of `reason`:
      - "<ASSET> QTY <quantity>" -> use the quantity exactly as given
        (this is what this app's own .txt export writes).
      - "<ASSET> <price>" -> derive quantity as amount / price (a
        convenience for hand-written notes; price is per-unit).
    Returns None if `reason` matches neither shape.
    """
    reason = reason or ""

    qty_match = _ASSET_QTY_RE.match(reason)
    if qty_match:
        quantity = float(qty_match.group("quantity").replace(",", ""))
        if quantity > 0:
            return qty_match.group("asset").upper(), quantity
        return None

    price_match = _ASSET_PRICE_RE.match(reason)
    if price_match:
        price = float(price_match.group("price").replace(",", ""))
        if price > 0:
            return price_match.group("asset").upper(), amount / price
        return None

    return None


def parse_ledger_line(line: str) -> dict | None:
    """
    Parse a single ledger line into a record dict
    {"amount", "is_income", "date", "person", "reason", "asset_type",
    "asset_quantity"}, or None if the line is blank/unparseable.
    """
    line = line.strip()
    if not line:
        return None

    match = _LEDGER_LINE_RE.match(line)
    if not match:
        return None

    tags = _TAG_RE.findall(match.group("rest"))
    raw_date = tags[0] if len(tags) > 0 else None
    if not raw_date:
        return None

    amount = float(match.group("amount").replace(",", ""))
    reason = tags[2].strip() if len(tags) > 2 else ""

    record = {
        "amount": amount,
        "is_income": match.group("sign") == "+",
        "date": normalize_date(raw_date),
        "person": tags[1].strip() if len(tags) > 1 and tags[1].strip() else None,
        "reason": reason,
        "asset_type": None,
        "asset_quantity": None,
    }

    asset = parse_asset_shorthand(reason, amount)
    if asset:
        record["asset_type"], record["asset_quantity"] = asset

    return record
