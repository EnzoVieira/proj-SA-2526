import asyncio
import random
import json
import logging

from typing import Final
from dataclasses import dataclass

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
_SERIAL_TIMEOUT: Final[int] = 1  # second
_INGESTER_TIMEOUT: Final[int] = 2  # seconds


# TODO: change this i have no clue how the f does the arduino ingester will work
@dataclass(slots=True)
class Ingester:
    _bus: EventBus
    _serial: Serial | None
    _debug: bool

    def __init__(self, bus: EventBus, *, debug: bool = False):
        self._bus = bus
        self._debug = debug
        if self._debug:
            self._serial = None
            log.warning("Running ingester in DEBUG mode")
        else:
            self._serial = Serial(_PORT, _BAUDRATE, timeout=_SERIAL_TIMEOUT)

    async def start(self):
        log.info("Arduino ingester started...")
        while True:
            try:
                if self._debug:
                    payload = self._generate_fake_data()
                else:
                    line = self._serial.readline().decode("utf-8").strip()
                    if not line:
                        continue
                    payload = json.loads(line)
                
                log.info(f"Ingesting sensor data: {payload}...")
                data = SensorData(**payload)
                await self._bus.publish(data)
            except Exception as e:
                log.error(f"Invalid data from Arduino: {e}...")

            await asyncio.sleep(_INGESTER_TIMEOUT)

    def stop(self):
        if self._serial:
            self._serial.close()
        log.info("Stoping ingester...")

    def _generate_fake_data(self) -> dict:
        return {
            "temperature": round(random.uniform(20, 35), 2),
            "humidity": round(random.uniform(40, 90), 2),
            "co2": random.randint(400, 2000),
        }
