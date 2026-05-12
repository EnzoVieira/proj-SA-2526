import asyncio
import json
import logging

from typing import Final
from dataclasses import dataclass

import serial
from serial import Serial

from pi_server.core.processor import Processor

"""
===============================================================================

    Ingester	

===============================================================================
"""

log = logging.getLogger(__name__)

_TIMEOUT: Final[int] = 1 # second

# TODO: change this i have no clue how the f does the arduino ingester will work
@dataclass(slots=True)
class Ingester:
    _serial: Serial
    _processor: Processor
    _running: bool

    def __init__(self, port: str, baudrate: int, processor):
        self._serial = Serial(port, baudrate, timeout=_TIMEOUT)
        self._processor = processor
        self._running = False

    async def start(self):
        self._running = True
        log.info("Arduino reader started...")

        while self._running:
            line = self._serial.readline().decode("utf-8").strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                await self._processor.add(data)
            except Exception as e:
                log.error(f"Invalid data from Arduino: {line} | {e}...")

            await asyncio.sleep(0)  # yield control

    def stop(self):
        self._running = False
        if self._serial:
            self._serial.close()
        log.info("Stoping ingester...")
