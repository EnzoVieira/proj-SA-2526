import random
import logging

from dataclasses import dataclass
from typing import Final

from pi_server.core.bus import EventBus
from pi_server.core.domain import ConditionLabel
from pi_server.ml.ml_model import MLModel
from pi_server.core.actions import ActionHandler

"""
===============================================================================

    Processor	

===============================================================================
"""

# TODO: finish this i no clue this shit url
_HOME_ASSISTANT_URL: Final[str] = "..."

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Processor:
    _bus: EventBus
    _model: MLModel | None
    _actions: ActionHandler
    _debug: bool

    def __init__(self, bus: EventBus, *, debug: bool = False):
        self._bus = bus
        self._debug = debug
        if self._debug:
            self._model = None
            log.warning("Processor in DEBUG MODE...")
        else:
            self._model = MLModel()
        self._actions = ActionHandler(_HOME_ASSISTANT_URL)

    async def start(self):
        log.info("Starting processor...")
        while True:
            data = await self._bus.consume()
            try:
                log.info(f"Predicting label of data: {data}...")
                if self._debug:
                    label = self._random_label()
                else:
                    label = self._model.predict(data)
                log.info(f"Handling label: {label}...")
                await self._actions.handle(label, data)
            except Exception as e:
                log.error(f"Error in worker: {e}...")
            finally:
                self._bus.task_done()

    async def stop(self):
        await self._actions.close()
        log.info("Stopping processor...")

    def _random_label(self) -> ConditionLabel:
        return random.choice(list(ConditionLabel))
