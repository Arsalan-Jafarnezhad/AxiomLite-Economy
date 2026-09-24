"""
USDT to IRT price app (async version using httpx)
"""

import asyncio
from pathlib import Path

import httpx

from .config import PRICE_CACHE_PATH

FALLBACK_PRICE = 167_000


async def _fetch_usd_irt(url: str | None = None) -> float | None:
    """
    Fetches USD to IRT price from Nobitex API using httpx.
    Returns None on any failure so the caller can fall back to cache.
    """
    if url is None:
        url = "https://apiv2.nobitex.ir/v3/orderbook/USDTIRT"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return 0.1 * float(data["lastTradePrice"])
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return None


async def _get_usd_irt(cache_path: Path = PRICE_CACHE_PATH) -> float:
    price = await _fetch_usd_irt()

    if price is not None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(str(price), encoding="utf-8")
        except OSError:
            pass
        return price

    # Live fetch failed -> try cache, then hard fallback
    if cache_path.exists():
        try:
            return float(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    return FALLBACK_PRICE


def get_usd_irt() -> float:
    return asyncio.run(_get_usd_irt())


# Gold price per gram in IRT (Toman). No live source is wired up yet -
# this is a placeholder with the same call shape as get_usd_irt() so
# swapping in a real fetch later (e.g. scraping a local gold-price
# site) is a drop-in change; nothing else in the app needs to change.
# Gold price per gram in IRT (Toman).
# Uses XAUS for live XAU/USD and the existing USD/IRT rate from Nobitex.

GOLD_PRICE_PLACEHOLDER = 20_000_000

GOLD_API_URL = "https://xaus.com/api/v1/spot"

# Iranian market gold is commonly quoted as 18K.
GOLD_PURITY = 18 / 24


async def _fetch_gold_irt() -> float | None:
    """
    Fetches the live 18K gold price per gram in IRT (Toman).

    XAUS provides the international XAU/USD price per gram.
    The existing USD/IRT function provides the local exchange rate.

    Returns None on any failure.
    """
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(GOLD_API_URL)
            response.raise_for_status()

            data = response.json()

            gold_usd_per_gram = float(data["per_gram_usd"])
            usd_irt = await _get_usd_irt()

            # 24K gold price per gram in Toman.
            gold_24k_irt = gold_usd_per_gram * usd_irt

            # Convert 24K to 18K.
            gold_18k_irt = gold_24k_irt * GOLD_PURITY

            return gold_18k_irt

    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return None


async def _get_gold_irt() -> float:
    """
    Returns the current 18K gold price per gram in IRT (Toman).

    Falls back to GOLD_PRICE_PLACEHOLDER if the live API fails.
    """
    price = await _fetch_gold_irt()

    if price is not None:
        return price

    return GOLD_PRICE_PLACEHOLDER


def get_gold_irt() -> float:
    """
    Synchronous wrapper around the async gold price fetcher.
    """
    return asyncio.run(_get_gold_irt())

if __name__ == "__main__":
    print(get_usd_irt())
