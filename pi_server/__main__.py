import asyncio

from pi_server.core.manager import Manager
from pi_server.utils.logger import get_logger

"""
===============================================================================

	Main

===============================================================================
"""

log = get_logger("server", console=True)


async def main():
    log.info("Starting server...")
    manager = Manager()
    try:
        await manager.start()
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Shutting down...")
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
