import logging

from dataclasses import dataclass

from pi_server.core.domain import ConditionLabel
from pi_server.utils.protocol import SensorData

"""
===============================================================================

	Action Handler

===============================================================================
"""

log = logging.getLogger(__name__)

# TODO: finish this according to the api (not sure of this)
@dataclass(slots=True)
class ActionHandler:
    async def handle(self, label: ConditionLabel, data: SensorData) -> None:
        if label == ConditionLabel.COLD:
            await self.cooling_system_on()

        else:
            log.info("Normal conditions...")

    async def cooling_system_on(self):
        log.info("Cooling system activated")

