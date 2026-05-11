import asyncio
import logging

from asyncio import Queue
from dataclasses import dataclass
from typing import Final

from pi_server.core.domain import SensorData
from pi_server.ml.ml_model import MLModel
from pi_server.core.actions import ActionHandler

"""
===============================================================================

    Processor	

===============================================================================
"""

_QUEUE_MAXSIZE: Final[int] = 100

log = logging.getLogger(__name__)

@dataclass(slots=True)
class Processor:
    queue: Queue[SensorData]
    model: MLModel
    actions: ActionHandler
    running: bool

    def __init__(self):
        self.queue = Queue(maxsize=_QUEUE_MAXSIZE)
        self.model = MLModel()
        self.actions = ActionHandler()
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self._worker())

    async def stop(self):
        self.running = False

    async def add(self, data: dict):
        data = SensorData(**data)
        await self.queue.put(data)

    async def _worker(self):
        log.info("Starting worker...")
        while self.running:
            data = await self.queue.get()
            try:
                label = self.model.predict(data)
                await self.actions.handle(label, data)
                log.info(f"Processing: {data} → {label}...")
            except Exception as e:
                log.error(f"Error in worker: {e}...")
            finally:
                self.queue.task_done()
