import logging

from typing import Final
from dataclasses import dataclass

import httpx
from httpx import AsyncClient

from pi_server.core.domain import ConditionLabel, SensorData

"""
===============================================================================

	Action Handler

===============================================================================
"""

log = logging.getLogger(__name__)

_TIMEOUT: Final[int] = 10  # seconds


# TODO: call the home assistant api, this is just an example...
@dataclass(slots=True)
class ActionHandler:
    api_base_url: str
    client: AsyncClient

    def __init__(self, url: str):
        self.api_base_url = url
        self.client = AsyncClient(timeout=_TIMEOUT)

    async def handle(self, label: ConditionLabel, data: SensorData) -> None:
        if label == ConditionLabel.COLD:
            await self.cooling_system_on(data)
        else:
            log.warning("Not existing label...")

    async def cooling_system_on(self, data: SensorData):
        log.info("Cooling system activated")
        payload = {
            "temperature": data.temperature,
            "humidity": data.humidity,
            "status": "on",
        }

        try:
            response = await self.client.post(
                f"{self.api_base_url}/cooling-system",
                json=payload,
            )
            response.raise_for_status()
            log.info("External API notified successfully")
        except httpx.HTTPError as e:
            log.error(f"Failed to call external API: {e}...")

    async def close(self):
        await self.client.aclose()
        log.info("Closing action handler...")
