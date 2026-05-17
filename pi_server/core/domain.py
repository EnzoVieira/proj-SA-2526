from enum import Enum

from pydantic import BaseModel

"""
===============================================================================

    Domain

===============================================================================
"""


class BlindsAction(str, Enum):
    RAISE = "raise"
    LOWER = "lower"
    KEEP = "keep"


class ACAction(str, Enum):
    OFF = "off"
    COOL = "cool"
    HEAT = "heat"


class DHT11Data(BaseModel):
    """Dados do sensor DHT11 (temperatura e humidade)"""
    temperature: float  # Celsius
    humidity: float     # Percentagem (%)


class LightSensorData(BaseModel):
    """Dados do sensor de luz analógico"""
    light_level: int    # 0-1023 (valor analógico)
    is_bright: bool     # True se light_level >= threshold


class SensorData(BaseModel):
    """Agregação de todos os dados de sensores"""
    dht11: DHT11Data
    light: LightSensorData
    timestamp: float | None = None


class Prediction(BaseModel):
    """Decisão composta do modelo ML"""
    blinds: BlindsAction
    ac: ACAction
    blinds_confidence: float | None = None
    ac_confidence: float | None = None
