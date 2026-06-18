import asyncio
import logging
import os
from stem import Signal
from stem.control import Controller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("deeptrawl.identity")


async def trigger_identity_renewal() -> bool:
    """Send NEWNYM signal to Tor ControlPort to rotate circuit identity."""
    port = int(os.environ.get("TOR_CONTROL_PORT", 9051))
    host = os.environ.get("TOR_CONTROL_HOST", "127.0.0.1")
    password = os.environ.get("TOR_CONTROL_PASSWORD", "")

    def _renew():
        try:
            with Controller.from_port(port=port, address=host) as controller:
                controller.authenticate(password=password) if password else controller.authenticate()
                controller.signal(Signal.NEWNYM)
                logger.info("Tor identity rotated successfully (NEWNYM)")
                return True
        except Exception as e:
            logger.error("Tor identity renewal failed: %s", e)
            return False

    return await asyncio.to_thread(_renew)
