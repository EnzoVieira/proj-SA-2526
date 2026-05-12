import asyncio
import logging

from asyncio import CancelledError, Queue, Task
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
_HOME_ASSISTANT_URL: Final[str] = "..."

log = logging.getLogger(__name__)

@dataclass(slots=True)
class Processor:
    _queue: Queue[SensorData]
    _model: MLModel
    _actions: ActionHandler
    _running: bool
    _task: Task | None = None

    def __init__(self):
        self._queue = Queue(maxsize=_QUEUE_MAXSIZE)
        self._model = MLModel()
        self._actions = ActionHandler(_HOME_ASSISTANT_URL)
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._worker())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._actions.close()

    async def add(self, data: dict):
        sensor_data = SensorData(**data)
        await self._queue.put(sensor_data)

    async def _worker(self):
        log.info("Starting worker...")
        try:
            while self._running:
                data = await self._queue.get()
                try:
                    log.info(f"Predicting label of data: {data}...")
                    label = self._model.predict(data)
                    log.info(f"Handling label: {label}...")
                    await self._actions.handle(label, data)
                except Exception as e:
                    log.error(f"Error in worker: {e}...")
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            log.info("Worker cancelled, shutting processor down...")
