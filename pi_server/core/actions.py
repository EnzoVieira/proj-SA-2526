import logging

from typing import Final
from dataclasses import dataclass

import httpx
from httpx import AsyncClient

from pi_server.core.domain import Prediction, SensorData

"""
===============================================================================

    Action Handler

===============================================================================
"""

log = logging.getLogger(__name__)

_TIMEOUT: Final[int] = 10  # seconds


# TODO: call the home assistant api with the proper service endpoints
@dataclass(slots=True)
class ActionHandler:
    api_base_url: str
    client: AsyncClient

    def __init__(self, url: str):
        self.api_base_url = url
        self.client = AsyncClient(timeout=_TIMEOUT)

    async def handle(self, prediction: Prediction, data: SensorData) -> None:
        log.info(
            f"Action plan: blinds={prediction.blinds.value}, ac={prediction.ac.value} "
            f"(temp={data.dht11.temperature}°C, humidity={data.dht11.humidity}%, "
            f"light={data.light.light_level})"
        )
        # TODO: dispatch to Home Assistant (cover.set_cover_position + climate.set_hvac_mode)

    async def close(self):
        await self.client.aclose()
        log.info("Closing action handler...")
