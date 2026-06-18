import asyncio
import aiohttp
import logging
import os
from aiohttp_socks import ProxyConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("deeptrawl.collector")

TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 20 * 1024 * 1024  # 20 MB per feed

renewal_lock = asyncio.Lock()


async def fetch_url(
    session: aiohttp.ClientSession, url: str, max_retries: int = 2
) -> dict:
    """Fetch a single feed URL with automatic retry and Tor identity rotation."""
    headers = {
        "User-Agent": "DeepTrawl/1.0",
        "Accept": "*/*",
        "Connection": "close",
    }

    for attempt in range(max_retries + 1):
        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
            ) as response:
                status = response.status
                if status in (403, 429, 503):
                    logger.warning("Rate limited (HTTP %d) on %s", status, url)
                    raise Exception(f"HTTP {status}")
                content = await response.text() if status == 200 else ""
                return {"url": url, "status": status, "content": content}
        except asyncio.TimeoutError:
            logger.warning("Timeout fetching %s (attempt %d/%d)", url, attempt + 1, max_retries + 1)
        except aiohttp.ClientError as e:
            logger.warning("Client error fetching %s: %s", url, e)
        except Exception as e:
            logger.warning("Unexpected error fetching %s: %s (%s)", url, e, type(e).__name__)

        if attempt < max_retries:
            if not renewal_lock.locked():
                async with renewal_lock:
                    from app.core.identity_manager import trigger_identity_renewal
                    await trigger_identity_renewal()
                    await asyncio.sleep(4)
            else:
                while renewal_lock.locked():
                    await asyncio.sleep(0.5)

    logger.error("All retries exhausted for %s", url)
    return {"url": url, "status": 0, "content": "", "error": "max_retries_exceeded"}


async def fetch_all(urls: list[str]) -> list[dict]:
    """Concurrent feed collection, routed through Tor SOCKS5 proxy when configured."""
    proxy = os.environ.get("UPSTREAM_PROXY")
    if proxy and proxy.startswith("socks5h://"):
        proxy = "socks5://" + proxy[len("socks5h://"):]  # python-socks 2.x compat

    connector = (
        ProxyConnector.from_url(proxy, limit_per_host=5, limit=50)
        if proxy
        else aiohttp.TCPConnector(limit_per_host=5, limit=50)
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            {"url": url, "status": 0, "content": "", "error": str(r)}
            if isinstance(r, Exception)
            else r
            for url, r in zip(urls, results)
        ]
