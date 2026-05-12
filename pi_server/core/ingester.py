import asyncio
import json
import logging

from typing import Final
from dataclasses import dataclass

import serial
from serial import Serial

from pi_server.core.bus import EventBus
from pi_server.core.domain import SensorData

"""
===============================================================================

    Ingester	

===============================================================================
"""

log = logging.getLogger(__name__)

# TODO: Finish this i dont even know wtf is a baudrate
_PORT: Final[str] = "..."
_BAUDRATE: Final[int] = 9600
_TIMEOUT: Final[int] = 1 # second

# TODO: change this i have no clue how the f does the arduino ingester will work
@dataclass(slots=True)
class Ingester:
    _bus: EventBus
    _serial: Serial

    def __init__(self, bus: EventBus):
        self._bus = bus
        self._serial = Serial(_PORT, _BAUDRATE, timeout=_TIMEOUT)

    async def start(self):
        log.info("Arduino ingester started...")

        while True:
            line = self._serial.readline().decode("utf-8").strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
                data = SensorData(**payload)
                await self._bus.publish(data)
            except Exception as e:
                log.error(f"Invalid data from Arduino: {line} | {e}...")

            await asyncio.sleep(0)  # yield control

    def stop(self):
        if self._serial:
            self._serial.close()
        log.info("Stoping ingester...")
