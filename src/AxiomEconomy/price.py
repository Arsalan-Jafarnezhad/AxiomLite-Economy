"""
USDT to IRT price app (async version using httpx)
"""
import asyncio
import os
import httpx

FALLBACK_PRICE = 167_000
CACHE_PATH = "./data.txt"


async def _fetch_usd_irt(url: str = None) -> float | None:
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


async def _get_usd_irt() -> float:
    price = await _fetch_usd_irt()

    if price is not None:
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as file:
                file.write(str(price))
        except OSError:
            pass
        return price

    # Live fetch failed -> try cache, then hard fallback
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as file:
                return float(file.read())
        except (OSError, ValueError):
            pass

    return FALLBACK_PRICE


def get_usd_irt() -> float:
    return asyncio.run(_get_usd_irt())


if __name__ == "__main__":
    print(get_usd_irt())