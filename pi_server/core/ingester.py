import asyncio
import random
import json
import logging
import time
import re

from typing import Final
from dataclasses import dataclass

from serial import Serial, SerialException
from serial.tools import list_ports

from pi_server.core.bus import EventBus
from pi_server.core.domain import SensorData, DHT11Data, LightSensorData

"""
===============================================================================

    Ingester	

===============================================================================
"""

log = logging.getLogger(__name__)

_PORT: Final[str] = "/dev/ttyACM0" #change where arduino is connected
_BAUDRATE: Final[int] = 9600
_SERIAL_TIMEOUT: Final[int] = 1  # second
_INGESTER_TIMEOUT: Final[int] = 2  # seconds
_LIGHT_THRESHOLD: Final[int] = 500

@dataclass(slots=True)
class Ingester:
    _bus: EventBus
    _serial: Serial | None
    _debug: bool
    _port: str | None = None
    _temp: float | None = None
    _humidity: float | None = None
    _light_level: int | None = None

    def __init__(self, bus: EventBus, *, debug: bool = False):
        self._bus = bus
        self._debug = debug
        self._temp = None
        self._humidity = None
        self._light_level = None
        
        if self._debug:
            self._serial = None
            self._port = None
            log.warning("Running ingester in DEBUG mode")
        else:
            # Determine preferred port now but do NOT open it yet.
            port = _PORT
            if not port or port == "...":
                ports = list(list_ports.comports())
                candidate = None
                for p in ports:
                    desc = (p.description or "").lower()
                    if "arduino" in desc or "usb" in desc or "wch" in desc or "ch340" in desc:
                        candidate = p.device
                        break
                if candidate is None and ports:
                    candidate = ports[0].device
                if candidate is None:
                    log.warning("No serial ports found at init. Will retry on start.")
                    port = None
                else:
                    port = candidate
                    log.info(f"Auto-detected serial port: {port}")

            self._serial = None
            self._port = port

    async def start(self):
        log.info("Arduino ingester started...")
        while True:
            try:
                if self._debug:
                    payload = self._generate_fake_data()
                    data = SensorData(**payload)
                    log.info(f"Ingesting (DEBUG) sensor data: {payload}...")
                    await self._bus.publish(data)
                else:
                    # Ensure serial is open, try to (re)connect if needed.
                    if self._serial is None:
                        try:
                            if not self._port:
                                # attempt auto-detect again
                                ports = list(list_ports.comports())
                                if ports:
                                    self._port = ports[0].device
                                    log.info(f"Auto-detected serial port on start: {self._port}")
                            if self._port:
                                self._serial = Serial(self._port, _BAUDRATE, timeout=_SERIAL_TIMEOUT)
                                log.info(f"Connected to serial port {self._port}")
                        except SerialException as e:
                            log.warning(f"Could not open serial port {self._port}: {e}")
                            self._serial = None
                            # skip reading this cycle
                            await asyncio.sleep(_INGESTER_TIMEOUT)
                            continue

                    if not self._serial:
                        await asyncio.sleep(_INGESTER_TIMEOUT)
                        continue

                    line = self._serial.readline().decode("utf-8").strip()
                    if not line:
                        continue
                    self._process_line(line)
            except Exception as e:
                log.error(f"Invalid data from Arduino: {e}...")

            await asyncio.sleep(_INGESTER_TIMEOUT)

    def _process_line(self, line: str):
        """Parse Arduino serial output and extract sensor data"""
        
        # Try JSON format first
        if line.startswith("{"):
            data = json.loads(line)
            sensor_data = self._parse_json_data(data)
            asyncio.create_task(self._bus.publish(sensor_data))
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
                asyncio.create_task(self._bus.publish(sensor_data))
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
        if self._serial:
            self._serial.close()
        log.info("Stopping ingester...")

    def _generate_fake_data(self) -> dict:
        """Generate fake sensor data for debug mode"""
        return {
            "dht11": {
                "temperature": round(random.uniform(20, 35), 2),
                "humidity": round(random.uniform(40, 90), 2),
            },
            "light": {
                "light_level": random.randint(0, 1023),
                "is_bright": random.choice([True, False]),
            }
        }
