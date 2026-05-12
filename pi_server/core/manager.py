import asyncio

from dataclasses import dataclass
from asyncio import Task 

from pi_server.core.bus import EventBus
from pi_server.core.processor import Processor
from pi_server.core.ingester import Ingester

"""
===============================================================================

	Manager

===============================================================================
"""

@dataclass(slots=True)
class Manager:
    _event_bus: EventBus
    _processor: Processor
    _ingester: Ingester
    _tasks: list[Task]

    def __init__(self) -> None:
        self._event_bus = EventBus()
        self._processor = Processor(self._event_bus)
        self._ingester = Ingester(self._event_bus)
        self._tasks = []

    async def start(self):
        self._tasks = [
            asyncio.create_task(self._processor.start),
            asyncio.create_task(self._ingester.start)
        ]

    async def stop(self):
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(
            *self._tasks,
            return_exceptions=True,
        )

        await self._processor.stop()
        self._ingester.stop()

    
