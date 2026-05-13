import asyncio
import json
import logging
import time
import re

from typing import Final
from dataclasses import dataclass

import serial
from serial import Serial

from pi_server.core.processor import Processor
from pi_server.core.domain import SensorData, DHT11Data, LightSensorData

"""
===============================================================================

    Ingester	

===============================================================================
"""

log = logging.getLogger(__name__)

_TIMEOUT: Final[int] = 1 # second
_LIGHT_THRESHOLD: Final[int] = 500

@dataclass(slots=True)
class Ingester:
    _serial: Serial
    _processor: Processor
    _running: bool
    _temp: float | None = None
    _humidity: float | None = None
    _light_level: int | None = None

    def __init__(self, port: str, baudrate: int, processor):
        self._serial = Serial(port, baudrate, timeout=_TIMEOUT)
        self._processor = processor
        self._running = False
        self._temp = None
        self._humidity = None
        self._light_level = None

    async def start(self):
        self._running = True
        log.info("Arduino reader started...")

        while self._running:
            line = self._serial.readline().decode("utf-8").strip()
            if not line:
                continue

            try:
                self._process_line(line)
            except Exception as e:
                log.error(f"Error processing line from Arduino: {line} | {e}...")

            await asyncio.sleep(0)  # yield control

    def _process_line(self, line: str):
        """Parse Arduino serial output and extract sensor data"""
        
        # Try JSON format first
        if line.startswith("{"):
            data = json.loads(line)
            sensor_data = self._parse_json_data(data)
            asyncio.create_task(self._processor.add(sensor_data.model_dump()))
            return

        # Parse text format from Arduino
        if "Luz:" in line:
            match = re.search(r"Luz:\s*(\d+)", line)
            if match:
                self._light_level = int(match.group(1))
                log.debug(f"Light level: {self._light_level}")

        if "Humidade:" in line and "Temperatura:" in line:
            humidity_match = re.search(r"Humidade:\s*([\d.]+)", line)
            temp_match = re.search(r"Temperatura:\s*([\d.]+)", line)
            
            if humidity_match:
                self._humidity = float(humidity_match.group(1))
            if temp_match:
                self._temp = float(temp_match.group(1))
            
            # When we have both temp and humidity, send data
            if self._temp is not None and self._humidity is not None and self._light_level is not None:
                sensor_data = self._create_sensor_data()
                asyncio.create_task(self._processor.add(sensor_data.model_dump()))
                # Reset for next reading
                self._temp = None
                self._humidity = None
                self._light_level = None

    def _parse_json_data(self, data: dict) -> SensorData:
        """Parse JSON format from Arduino"""
        dht11_data = DHT11Data(
            temperature=data.get("temperature", 0.0),
            humidity=data.get("humidity", 0.0)
        )
        
        light_level = data.get("light_level", 0)
        light_data = LightSensorData(
            light_level=light_level,
            is_bright=light_level >= _LIGHT_THRESHOLD
        )
        
        return SensorData(
            dht11=dht11_data,
            light=light_data,
            timestamp=time.time()
        )

    def _create_sensor_data(self) -> SensorData:
        """Create SensorData from collected readings"""
        dht11_data = DHT11Data(
            temperature=self._temp or 0.0,
            humidity=self._humidity or 0.0
        )
        
        light_level = self._light_level or 0
        light_data = LightSensorData(
            light_level=light_level,
            is_bright=light_level >= _LIGHT_THRESHOLD
        )
        
        log.info(f"Sensor data: Temp={self._temp}°C, Humidity={self._humidity}%, Light={self._light_level}")
        
        return SensorData(
            dht11=dht11_data,
            light=light_data,
            timestamp=time.time()
        )

    def stop(self):
        self._running = False
        if self._serial:
            self._serial.close()
        log.info("Stopping ingester...")
