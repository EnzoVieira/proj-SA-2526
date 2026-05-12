from dataclasses import dataclass

from pi_server.core.processor import Processor
from pi_server.core.ingester import Ingester

"""
===============================================================================

	Manager

===============================================================================
"""

@dataclass(slots=True)
class Manager:
    _processor: Processor
    _ingester: Ingester

    def __init__(self) -> None:
        self._processor = Processor()
        self._ingester = Ingester(self._processor)

    async def start(self):
        await self._processor.start()
        await self._ingester.start()

    async def stop(self):
        await self._processor.stop()
        self._ingester.stop()

    
