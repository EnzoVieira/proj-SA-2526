import logging
import os

from typing import Final
from dataclasses import dataclass

from httpx import AsyncClient, HTTPError

from pi_server.core.comfort_policy import decide
from pi_server.core.domain import Prediction, SensorData

"""
===============================================================================

    Action Handler

===============================================================================
"""

log = logging.getLogger(__name__)

_TIMEOUT: Final[int] = 10  # seconds


@dataclass(slots=True)
class ActionHandler:
    _client: AsyncClient
    _base_url: str
    _ac_entity: str
    _blinds_entity: str
    _last_hvac_mode: str | None
    _last_cover_op: str | None

    def __init__(self):
        self._base_url = os.environ["HA_BASE_URL"].rstrip("/")
        token = os.environ["HA_TOKEN"]
        self._ac_entity = os.environ["HA_AC_ENTITY"]
        self._blinds_entity = os.environ["HA_BLINDS_ENTITY"]

        self._client = AsyncClient(
            timeout=_TIMEOUT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        self._last_hvac_mode = None
        self._last_cover_op = None

    async def handle(self, prediction: Prediction, data: SensorData) -> None:
        decision = decide(prediction)
        log.info(
            f"Action plan: thermal={prediction.thermal.value}, lum={prediction.luminosity.value} "
            f"-> hvac={decision.hvac_mode}, cover={decision.cover_op} "
            f"(temp={data.dht11.temperature}°C, humidity={data.dht11.humidity}%, "
            f"light={data.light.light_level})"
        )

        await self._set_hvac_mode(decision.hvac_mode)
        await self._operate_blinds(decision.cover_op)

    async def _set_hvac_mode(self, hvac_mode: str | None) -> None:
        if hvac_mode is None:
            return
        if hvac_mode == self._last_hvac_mode:
            return

        url = f"{self._base_url}/api/services/climate/set_hvac_mode"
        body = {"entity_id": self._ac_entity, "hvac_mode": hvac_mode}
        try:
            response = await self._client.post(url, json=body)
            response.raise_for_status()
        except HTTPError as e:
            log.warning(f"HA set_hvac_mode={hvac_mode} failed: {e}")
            return

        self._last_hvac_mode = hvac_mode
        log.info(f"HA: AC set to hvac_mode={hvac_mode}")

    async def _operate_blinds(self, cover_op: str | None) -> None:
        if cover_op is None:
            return
        if cover_op == self._last_cover_op:
            return

        url = f"{self._base_url}/api/services/cover/{cover_op}"
        body = {"entity_id": self._blinds_entity}
        try:
            response = await self._client.post(url, json=body)
            response.raise_for_status()
        except HTTPError as e:
            log.warning(f"HA cover/{cover_op} failed: {e}")
            return

        self._last_cover_op = cover_op
        log.info(f"HA: blinds {cover_op}")

    async def close(self):
        await self._client.aclose()
        log.info("Closing action handler...")
