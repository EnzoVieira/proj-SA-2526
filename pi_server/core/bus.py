from asyncio import Queue

from typing import Final
from dataclasses import dataclass

from pi_server.core.domain import SensorData

"""
===============================================================================

    Event Bus 

===============================================================================
"""

_QUEUE_MAXSIZE: Final[int] = 100


@dataclass(slots=True)
class EventBus:
    _queue: Queue[SensorData]

    def __init__(self) -> None:
        self._queue = Queue(maxsize=_QUEUE_MAXSIZE)

    async def publish(self, data: SensorData) -> None:
        await self._queue.put(data)

    async def consume(self) -> SensorData:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()
